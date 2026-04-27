"""
Stripe API routes.

Intended responsibilities (no implementation yet):
- Webhook endpoint (signature-verified, no user auth dependency)
- Checkout session creation (org-scoped, requires user auth)
- Billing portal session creation (org-scoped, requires user auth)

Keep this file thin: route handlers should delegate to `app/stripe/*`.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from stripe.params.billing_portal._session_create_params import (
    SessionCreateParamsFlowData as BillingPortalSessionCreateParamsFlowData,
)

from app.api.deps import get_supabase_client
from app.api.org_deps import OrgRoleContext, require_org_role
from app.database.organizations import OrganizationsHandler
from app.database.stripe_catalog_items import StripeCatalogItemsHandler
from app.database.stripe_webhook_events import StripeWebhookEventsHandler
from app.database.types_autogen import PublicOrganizations, PublicStripeCatalogItems
from app.stripe.checkout import create_checkout_session
from app.stripe.customers import create_stripe_customer, get_or_create_stripe_customer
from app.stripe.display import enrich_catalog_items_with_display_prices
from app.stripe.portal import create_billing_portal_session
from app.stripe.webhooks import (
    construct_event,
    event_to_json_dict,
    get_or_create_webhook_event_row,
    handle_checkout_session_completed,
    handle_customer_subscription_event,
    handle_invoice_payment_failed,
    handle_invoice_payment_succeeded,
    mark_event_failed,
    mark_event_processed,
    resolve_organization_id,
    should_process_event,
    summarize_event,
)
from app.utils.logger import get_logger
from supabase import Client

logger = get_logger(__name__)


class CreateStripeCustomerResponse(PublicOrganizations):
    pass


class CreateStripeCustomerRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # Optional override; defaults to current auth user's email (from bearer token).
    billing_email: str | None = None


class PublicStripeCatalogItemsWithDisplayPrices(PublicStripeCatalogItems):
    display_price: str | None = None
    display_price_discounted: str | None = None


class CreateCheckoutSessionRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    catalog_key: str
    success_url: str
    cancel_url: str


class CreateCheckoutSessionResponse(BaseModel):
    id: str
    url: str


class CreateBillingPortalSessionRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    return_url: str
    flow_data: BillingPortalSessionCreateParamsFlowData | None = None


class CreateBillingPortalSessionResponse(BaseModel):
    url: str


router = APIRouter(tags=['stripe'])

org_router = APIRouter(prefix='/org/{organization_id}/stripe')

webhook_router = APIRouter(prefix='/stripe')


@webhook_router.get('/catalog', response_model=list[PublicStripeCatalogItemsWithDisplayPrices])
def list_stripe_catalog_items(
    billing_type: str | None = None,
    db: Client = Depends(get_supabase_client),
) -> list[PublicStripeCatalogItemsWithDisplayPrices]:
    if billing_type is not None and billing_type not in ['subscription', 'one_off']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='billing_type must be one of: subscription, one_off',
        )

    catalog = StripeCatalogItemsHandler(db)
    items = catalog.list_catalog_items(billing_type=billing_type)

    enriched = enrich_catalog_items_with_display_prices(items)
    return [
        PublicStripeCatalogItemsWithDisplayPrices.model_validate(item_dict)
        for item_dict in enriched
    ]


@webhook_router.post('/webhook')
async def stripe_webhook(
    request: Request,
    db: Client = Depends(get_supabase_client),
) -> dict[str, bool]:
    signature = request.headers.get('stripe-signature')
    if signature is None or signature.strip() == '':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Missing Stripe-Signature'
        )

    payload = await request.body()
    try:
        event = construct_event(payload=payload, signature=signature)
        summary = summarize_event(event)
    except ValueError as exc:
        logger.warning('stripe webhook invalid payload/signature: %s', str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid Stripe payload'
        ) from exc

    event_json = event_to_json_dict(event)
    row, _created = get_or_create_webhook_event_row(db=db, summary=summary, event_json=event_json)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid Stripe payload'
        )

    resolved_org_id = resolve_organization_id(db=db, event=event, summary=summary, row=row)
    if resolved_org_id is not None:
        row = StripeWebhookEventsHandler(db).update_organization_id(
            row.id, organization_id=resolved_org_id
        )

    if not should_process_event(row):
        logger.warning(
            'stripe webhook skipping (already processed) event_id=%s type=%s',
            summary.event_id,
            summary.event_type,
        )
        return {'received': True}

    event_type = summary.event_type
    if event_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid Stripe payload'
        )

    try:
        organization_id = row.organization_id
        if event_type.startswith('customer.subscription.'):
            handle_customer_subscription_event(db=db, event=event, organization_id=organization_id)
        elif event_type == 'invoice.payment_succeeded':
            handle_invoice_payment_succeeded(db=db, event=event, organization_id=organization_id)
        elif event_type == 'invoice.payment_failed':
            handle_invoice_payment_failed(db=db, event=event, organization_id=organization_id)
        elif event_type == 'checkout.session.completed':
            handle_checkout_session_completed(event=event, organization_id=organization_id)
        else:
            logger.warning('stripe webhook ignoring type=%s', event_type)

        mark_event_processed(db=db, row_id=row.id)
    except Exception as exc:
        logger.exception('stripe webhook processing failed')
        mark_event_failed(db=db, row_id=row.id, error_message=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Webhook processing failed'
        ) from exc

    return {'received': True}


@org_router.post('/customer', response_model=CreateStripeCustomerResponse)
def create_org_stripe_customer(
    organization_id: UUID,
    payload: CreateStripeCustomerRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('owner')),
) -> CreateStripeCustomerResponse:
    if ctx.user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User token required')
    org, current_user = ctx.org, ctx.user
    organizations = OrganizationsHandler(db)

    existing_customer_id = org.stripe_customer_id
    if existing_customer_id is not None and existing_customer_id.strip() != '':
        return CreateStripeCustomerResponse.model_validate(org, from_attributes=True)

    billing_email = payload.billing_email or current_user.email
    if not billing_email or billing_email.strip() == '':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='billing_email is required',
        )

    customer_id = create_stripe_customer(
        organization_id=organization_id,
        name=org.name,
        email=billing_email,
    )

    updated = organizations.set_stripe_customer(
        organization_id,
        stripe_customer_id=customer_id,
        billing_email=billing_email,
    )
    return CreateStripeCustomerResponse.model_validate(updated, from_attributes=True)


@org_router.post('/checkout-session', response_model=CreateCheckoutSessionResponse)
def create_org_checkout_session(
    organization_id: UUID,
    payload: CreateCheckoutSessionRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('owner')),
) -> CreateCheckoutSessionResponse:
    if ctx.user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User token required')
    org, current_user = ctx.org, ctx.user
    if payload.success_url.strip() == '' or payload.cancel_url.strip() == '':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='success_url and cancel_url are required',
        )

    organizations = OrganizationsHandler(db)

    billing_email = org.billing_email or current_user.email
    if not billing_email or billing_email.strip() == '':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='billing_email is required to create a Stripe customer',
        )

    customer = get_or_create_stripe_customer(
        existing_customer_id=org.stripe_customer_id,
        organization_id=organization_id,
        name=org.name,
        email=billing_email,
    )
    stripe_customer_id = customer.stripe_customer_id
    if customer.is_new:
        org = organizations.set_stripe_customer(
            organization_id,
            stripe_customer_id=stripe_customer_id,
            billing_email=billing_email,
        )

    catalog = StripeCatalogItemsHandler(db)
    item = catalog.get_by_key(payload.catalog_key)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Catalog item not found',
        )

    session = create_checkout_session(
        organization_id=organization_id,
        stripe_customer_id=stripe_customer_id,
        catalog_item=item,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
        actor_user_id=current_user.id,
    )
    return CreateCheckoutSessionResponse.model_validate(session)


@org_router.post('/billing-portal-session', response_model=CreateBillingPortalSessionResponse)
def create_org_billing_portal_session(
    organization_id: UUID,
    payload: CreateBillingPortalSessionRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('owner')),
) -> CreateBillingPortalSessionResponse:
    if ctx.user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User token required')
    org, current_user = ctx.org, ctx.user
    if payload.return_url.strip() == '':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='return_url is required',
        )

    organizations = OrganizationsHandler(db)

    billing_email = org.billing_email or current_user.email
    if not billing_email or billing_email.strip() == '':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='billing_email is required to create a Stripe customer',
        )

    customer = get_or_create_stripe_customer(
        existing_customer_id=org.stripe_customer_id,
        organization_id=organization_id,
        name=org.name,
        email=billing_email,
    )
    stripe_customer_id = customer.stripe_customer_id
    if customer.is_new:
        _ = organizations.set_stripe_customer(
            organization_id,
            stripe_customer_id=stripe_customer_id,
            billing_email=billing_email,
        )

    session = create_billing_portal_session(
        stripe_customer_id=stripe_customer_id,
        return_url=payload.return_url,
        flow_data=payload.flow_data,
    )
    return CreateBillingPortalSessionResponse(url=session['url'])


# Include sub-routers after route registration so FastAPI captures all routes.
router.include_router(org_router)
router.include_router(webhook_router)
