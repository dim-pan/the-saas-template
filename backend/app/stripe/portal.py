from stripe.params.billing_portal._session_create_params import (
    SessionCreateParams as BillingPortalSessionCreateParams,
)
from stripe.params.billing_portal._session_create_params import (
    SessionCreateParamsFlowData as BillingPortalSessionCreateParamsFlowData,
)

from app.config import STRIPE_BILLING_PORTAL_CONFIGURATION_ID
from app.stripe.client import get_stripe_client


def create_billing_portal_session(
    *,
    stripe_customer_id: str,
    return_url: str,
    flow_data: BillingPortalSessionCreateParamsFlowData | None = None,
) -> dict[str, str]:
    if stripe_customer_id.strip() == '':
        raise ValueError('stripe_customer_id is required')
    if return_url.strip() == '':
        raise ValueError('return_url is required')

    params: BillingPortalSessionCreateParams = {
        'customer': stripe_customer_id,
        'return_url': return_url,
    }
    configuration_id = STRIPE_BILLING_PORTAL_CONFIGURATION_ID
    if configuration_id is not None and configuration_id.strip() != '':
        params['configuration'] = configuration_id
    if flow_data is not None:
        params['flow_data'] = flow_data

    client = get_stripe_client()
    session = client.v1.billing_portal.sessions.create(params)
    session_id = session.id
    session_url = session.url
    if not session_id or session_id.strip() == '':
        raise ValueError('Stripe billing portal session creation failed (missing id)')
    if not session_url or session_url.strip() == '':
        raise ValueError('Stripe billing portal session creation failed (missing url)')
    return {'id': session_id, 'url': session_url}
