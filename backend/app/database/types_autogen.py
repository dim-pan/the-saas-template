from __future__ import annotations

import datetime
import uuid
from typing import (
    Annotated,
    Any,
    List,
    Literal,
    NotRequired,
    Optional,
    TypeAlias,
    TypedDict,
)

from pydantic import BaseModel, Field

NetRequestStatus: TypeAlias = Literal['PENDING', 'SUCCESS', 'ERROR']

RealtimeEqualityOp: TypeAlias = Literal['eq', 'neq', 'lt', 'lte', 'gt', 'gte', 'in']

RealtimeAction: TypeAlias = Literal['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'ERROR']

StorageBuckettype: TypeAlias = Literal['STANDARD', 'ANALYTICS', 'VECTOR']

AuthFactorType: TypeAlias = Literal['totp', 'webauthn', 'phone']

AuthFactorStatus: TypeAlias = Literal['unverified', 'verified']

AuthAalLevel: TypeAlias = Literal['aal1', 'aal2', 'aal3']

AuthCodeChallengeMethod: TypeAlias = Literal['s256', 'plain']

AuthOneTimeTokenType: TypeAlias = Literal[
    'confirmation_token',
    'reauthentication_token',
    'recovery_token',
    'email_change_token_new',
    'email_change_token_current',
    'phone_change_token',
]

AuthOauthRegistrationType: TypeAlias = Literal['dynamic', 'manual']

AuthOauthAuthorizationStatus: TypeAlias = Literal['pending', 'approved', 'denied', 'expired']

AuthOauthResponseType: TypeAlias = Literal['code']

AuthOauthClientType: TypeAlias = Literal['public', 'confidential']


class PublicUsers(BaseModel):
    additional_data: dict[str, Any] = Field(alias='additional_data')
    archived: bool = Field(alias='archived')
    avatar_url: Optional[str] = Field(alias='avatar_url')
    created_at: datetime.datetime = Field(alias='created_at')
    email: str = Field(alias='email')
    full_name: Optional[str] = Field(alias='full_name')
    id: uuid.UUID = Field(alias='id')
    updated_at: Optional[datetime.datetime] = Field(alias='updated_at')
    username: Optional[str] = Field(alias='username')


class PublicUsersInsert(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    avatar_url: NotRequired[Annotated[Optional[str], Field(alias='avatar_url')]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    email: Annotated[str, Field(alias='email')]
    full_name: NotRequired[Annotated[Optional[str], Field(alias='full_name')]]
    id: Annotated[uuid.UUID, Field(alias='id')]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]
    username: NotRequired[Annotated[Optional[str], Field(alias='username')]]


class PublicUsersUpdate(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    avatar_url: NotRequired[Annotated[Optional[str], Field(alias='avatar_url')]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    email: NotRequired[Annotated[str, Field(alias='email')]]
    full_name: NotRequired[Annotated[Optional[str], Field(alias='full_name')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]
    username: NotRequired[Annotated[Optional[str], Field(alias='username')]]


class PublicOrganizations(BaseModel):
    additional_data: dict[str, Any] = Field(alias='additional_data')
    archived: bool = Field(alias='archived')
    billing_cancel_at_period_end: bool = Field(alias='billing_cancel_at_period_end')
    billing_current_period_end: Optional[datetime.datetime] = Field(
        alias='billing_current_period_end'
    )
    billing_current_period_start: Optional[datetime.datetime] = Field(
        alias='billing_current_period_start'
    )
    billing_email: Optional[str] = Field(alias='billing_email')
    billing_is_paid: bool = Field(alias='billing_is_paid')
    billing_plan_key: Optional[str] = Field(alias='billing_plan_key')
    billing_status: Optional[str] = Field(alias='billing_status')
    billing_updated_at: Optional[datetime.datetime] = Field(alias='billing_updated_at')
    created_at: datetime.datetime = Field(alias='created_at')
    id: uuid.UUID = Field(alias='id')
    name: str = Field(alias='name')
    stripe_customer_id: Optional[str] = Field(alias='stripe_customer_id')
    updated_at: Optional[datetime.datetime] = Field(alias='updated_at')


class PublicOrganizationsInsert(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    billing_cancel_at_period_end: NotRequired[
        Annotated[bool, Field(alias='billing_cancel_at_period_end')]
    ]
    billing_current_period_end: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='billing_current_period_end')]
    ]
    billing_current_period_start: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='billing_current_period_start')]
    ]
    billing_email: NotRequired[Annotated[Optional[str], Field(alias='billing_email')]]
    billing_is_paid: NotRequired[Annotated[bool, Field(alias='billing_is_paid')]]
    billing_plan_key: NotRequired[Annotated[Optional[str], Field(alias='billing_plan_key')]]
    billing_status: NotRequired[Annotated[Optional[str], Field(alias='billing_status')]]
    billing_updated_at: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='billing_updated_at')]
    ]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    name: Annotated[str, Field(alias='name')]
    stripe_customer_id: NotRequired[Annotated[Optional[str], Field(alias='stripe_customer_id')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]


class PublicOrganizationsUpdate(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    billing_cancel_at_period_end: NotRequired[
        Annotated[bool, Field(alias='billing_cancel_at_period_end')]
    ]
    billing_current_period_end: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='billing_current_period_end')]
    ]
    billing_current_period_start: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='billing_current_period_start')]
    ]
    billing_email: NotRequired[Annotated[Optional[str], Field(alias='billing_email')]]
    billing_is_paid: NotRequired[Annotated[bool, Field(alias='billing_is_paid')]]
    billing_plan_key: NotRequired[Annotated[Optional[str], Field(alias='billing_plan_key')]]
    billing_status: NotRequired[Annotated[Optional[str], Field(alias='billing_status')]]
    billing_updated_at: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='billing_updated_at')]
    ]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    name: NotRequired[Annotated[str, Field(alias='name')]]
    stripe_customer_id: NotRequired[Annotated[Optional[str], Field(alias='stripe_customer_id')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]


class PublicMemberships(BaseModel):
    additional_data: dict[str, Any] = Field(alias='additional_data')
    archived: bool = Field(alias='archived')
    created_at: datetime.datetime = Field(alias='created_at')
    id: uuid.UUID = Field(alias='id')
    invitation_expires_at: Optional[datetime.datetime] = Field(alias='invitation_expires_at')
    invitation_id: Optional[str] = Field(alias='invitation_id')
    invited_by_id: Optional[uuid.UUID] = Field(alias='invited_by_id')
    invited_email: Optional[str] = Field(alias='invited_email')
    organization_id: uuid.UUID = Field(alias='organization_id')
    role: str = Field(alias='role')
    updated_at: Optional[datetime.datetime] = Field(alias='updated_at')
    user_id: Optional[uuid.UUID] = Field(alias='user_id')


class PublicMembershipsInsert(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    invitation_expires_at: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='invitation_expires_at')]
    ]
    invitation_id: NotRequired[Annotated[Optional[str], Field(alias='invitation_id')]]
    invited_by_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias='invited_by_id')]]
    invited_email: NotRequired[Annotated[Optional[str], Field(alias='invited_email')]]
    organization_id: Annotated[uuid.UUID, Field(alias='organization_id')]
    role: NotRequired[Annotated[str, Field(alias='role')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]
    user_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias='user_id')]]


class PublicMembershipsUpdate(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    invitation_expires_at: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='invitation_expires_at')]
    ]
    invitation_id: NotRequired[Annotated[Optional[str], Field(alias='invitation_id')]]
    invited_by_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias='invited_by_id')]]
    invited_email: NotRequired[Annotated[Optional[str], Field(alias='invited_email')]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias='organization_id')]]
    role: NotRequired[Annotated[str, Field(alias='role')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]
    user_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias='user_id')]]


class PublicSubscriptions(BaseModel):
    additional_data: dict[str, Any] = Field(alias='additional_data')
    archived: bool = Field(alias='archived')
    cancel_at_period_end: bool = Field(alias='cancel_at_period_end')
    cancel_request_at: Optional[datetime.datetime] = Field(alias='cancel_request_at')
    created_at: datetime.datetime = Field(alias='created_at')
    current_period_end: Optional[datetime.datetime] = Field(alias='current_period_end')
    current_period_start: Optional[datetime.datetime] = Field(alias='current_period_start')
    ended_at: Optional[datetime.datetime] = Field(alias='ended_at')
    id: uuid.UUID = Field(alias='id')
    organization_id: uuid.UUID = Field(alias='organization_id')
    status: str = Field(alias='status')
    stripe_customer_id: Optional[str] = Field(alias='stripe_customer_id')
    stripe_price_id: str = Field(alias='stripe_price_id')
    stripe_product_id: str = Field(alias='stripe_product_id')
    stripe_subscription_id: str = Field(alias='stripe_subscription_id')
    stripe_subscription_item_id: Optional[str] = Field(alias='stripe_subscription_item_id')
    trial_end: Optional[datetime.datetime] = Field(alias='trial_end')
    updated_at: Optional[datetime.datetime] = Field(alias='updated_at')


class PublicSubscriptionsInsert(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    cancel_at_period_end: NotRequired[Annotated[bool, Field(alias='cancel_at_period_end')]]
    cancel_request_at: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='cancel_request_at')]
    ]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    current_period_end: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='current_period_end')]
    ]
    current_period_start: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='current_period_start')]
    ]
    ended_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='ended_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    organization_id: Annotated[uuid.UUID, Field(alias='organization_id')]
    status: Annotated[str, Field(alias='status')]
    stripe_customer_id: NotRequired[Annotated[Optional[str], Field(alias='stripe_customer_id')]]
    stripe_price_id: Annotated[str, Field(alias='stripe_price_id')]
    stripe_product_id: Annotated[str, Field(alias='stripe_product_id')]
    stripe_subscription_id: Annotated[str, Field(alias='stripe_subscription_id')]
    stripe_subscription_item_id: NotRequired[
        Annotated[Optional[str], Field(alias='stripe_subscription_item_id')]
    ]
    trial_end: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='trial_end')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]


class PublicSubscriptionsUpdate(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    cancel_at_period_end: NotRequired[Annotated[bool, Field(alias='cancel_at_period_end')]]
    cancel_request_at: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='cancel_request_at')]
    ]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    current_period_end: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='current_period_end')]
    ]
    current_period_start: NotRequired[
        Annotated[Optional[datetime.datetime], Field(alias='current_period_start')]
    ]
    ended_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='ended_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias='organization_id')]]
    status: NotRequired[Annotated[str, Field(alias='status')]]
    stripe_customer_id: NotRequired[Annotated[Optional[str], Field(alias='stripe_customer_id')]]
    stripe_price_id: NotRequired[Annotated[str, Field(alias='stripe_price_id')]]
    stripe_product_id: NotRequired[Annotated[str, Field(alias='stripe_product_id')]]
    stripe_subscription_id: NotRequired[Annotated[str, Field(alias='stripe_subscription_id')]]
    stripe_subscription_item_id: NotRequired[
        Annotated[Optional[str], Field(alias='stripe_subscription_item_id')]
    ]
    trial_end: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='trial_end')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]


class PublicStripeWebhookEvents(BaseModel):
    additional_data: dict[str, Any] = Field(alias='additional_data')
    created_at: datetime.datetime = Field(alias='created_at')
    id: uuid.UUID = Field(alias='id')
    livemode: bool = Field(alias='livemode')
    organization_id: Optional[uuid.UUID] = Field(alias='organization_id')
    payload: dict[str, Any] = Field(alias='payload')
    processed_at: Optional[datetime.datetime] = Field(alias='processed_at')
    processing_error: Optional[str] = Field(alias='processing_error')
    received_at: datetime.datetime = Field(alias='received_at')
    stripe_customer_id: Optional[str] = Field(alias='stripe_customer_id')
    stripe_event_id: str = Field(alias='stripe_event_id')
    type: str = Field(alias='type')
    updated_at: Optional[datetime.datetime] = Field(alias='updated_at')


class PublicStripeWebhookEventsInsert(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    livemode: Annotated[bool, Field(alias='livemode')]
    organization_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias='organization_id')]]
    payload: NotRequired[Annotated[dict[str, Any], Field(alias='payload')]]
    processed_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='processed_at')]]
    processing_error: NotRequired[Annotated[Optional[str], Field(alias='processing_error')]]
    received_at: NotRequired[Annotated[datetime.datetime, Field(alias='received_at')]]
    stripe_customer_id: NotRequired[Annotated[Optional[str], Field(alias='stripe_customer_id')]]
    stripe_event_id: Annotated[str, Field(alias='stripe_event_id')]
    type: Annotated[str, Field(alias='type')]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]


class PublicStripeWebhookEventsUpdate(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    livemode: NotRequired[Annotated[bool, Field(alias='livemode')]]
    organization_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias='organization_id')]]
    payload: NotRequired[Annotated[dict[str, Any], Field(alias='payload')]]
    processed_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='processed_at')]]
    processing_error: NotRequired[Annotated[Optional[str], Field(alias='processing_error')]]
    received_at: NotRequired[Annotated[datetime.datetime, Field(alias='received_at')]]
    stripe_customer_id: NotRequired[Annotated[Optional[str], Field(alias='stripe_customer_id')]]
    stripe_event_id: NotRequired[Annotated[str, Field(alias='stripe_event_id')]]
    type: NotRequired[Annotated[str, Field(alias='type')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]


class PublicAssets(BaseModel):
    asset_id: uuid.UUID = Field(alias='asset_id')
    created_at: datetime.datetime = Field(alias='created_at')
    deleted_at: Optional[datetime.datetime] = Field(alias='deleted_at')
    filename: str = Field(alias='filename')
    id: uuid.UUID = Field(alias='id')
    mime_type: str = Field(alias='mime_type')
    organization_id: uuid.UUID = Field(alias='organization_id')
    provider: str = Field(alias='provider')
    size_bytes: Optional[int] = Field(alias='size_bytes')
    status: str = Field(alias='status')
    storage_key: str = Field(alias='storage_key')
    thumbnail_url: Optional[str] = Field(alias='thumbnail_url')
    updated_at: Optional[datetime.datetime] = Field(alias='updated_at')
    user_id: Optional[uuid.UUID] = Field(alias='user_id')


class PublicAssetsInsert(TypedDict):
    asset_id: Annotated[uuid.UUID, Field(alias='asset_id')]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    deleted_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='deleted_at')]]
    filename: Annotated[str, Field(alias='filename')]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    mime_type: Annotated[str, Field(alias='mime_type')]
    organization_id: Annotated[uuid.UUID, Field(alias='organization_id')]
    provider: Annotated[str, Field(alias='provider')]
    size_bytes: NotRequired[Annotated[Optional[int], Field(alias='size_bytes')]]
    status: NotRequired[Annotated[str, Field(alias='status')]]
    storage_key: Annotated[str, Field(alias='storage_key')]
    thumbnail_url: NotRequired[Annotated[Optional[str], Field(alias='thumbnail_url')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]
    user_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias='user_id')]]


class PublicAssetsUpdate(TypedDict):
    asset_id: NotRequired[Annotated[uuid.UUID, Field(alias='asset_id')]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    deleted_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='deleted_at')]]
    filename: NotRequired[Annotated[str, Field(alias='filename')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    mime_type: NotRequired[Annotated[str, Field(alias='mime_type')]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias='organization_id')]]
    provider: NotRequired[Annotated[str, Field(alias='provider')]]
    size_bytes: NotRequired[Annotated[Optional[int], Field(alias='size_bytes')]]
    status: NotRequired[Annotated[str, Field(alias='status')]]
    storage_key: NotRequired[Annotated[str, Field(alias='storage_key')]]
    thumbnail_url: NotRequired[Annotated[Optional[str], Field(alias='thumbnail_url')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]
    user_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias='user_id')]]


class PublicStripeCatalogItems(BaseModel):
    additional_data: dict[str, Any] = Field(alias='additional_data')
    archived: bool = Field(alias='archived')
    billing_interval: Optional[str] = Field(alias='billing_interval')
    billing_interval_count: Optional[int] = Field(alias='billing_interval_count')
    billing_type: str = Field(alias='billing_type')
    created_at: datetime.datetime = Field(alias='created_at')
    default_stripe_coupon_id: Optional[str] = Field(alias='default_stripe_coupon_id')
    description: Optional[str] = Field(alias='description')
    feature_set: List[str] = Field(alias='feature_set')
    id: uuid.UUID = Field(alias='id')
    key: str = Field(alias='key')
    name: Optional[str] = Field(alias='name')
    override_stripe_coupon_id: Optional[str] = Field(alias='override_stripe_coupon_id')
    plan_family: Optional[str] = Field(alias='plan_family')
    rank: Optional[int] = Field(alias='rank')
    stripe_price_id: str = Field(alias='stripe_price_id')
    stripe_product_id: str = Field(alias='stripe_product_id')
    updated_at: Optional[datetime.datetime] = Field(alias='updated_at')


class PublicStripeCatalogItemsInsert(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    billing_interval: NotRequired[Annotated[Optional[str], Field(alias='billing_interval')]]
    billing_interval_count: NotRequired[
        Annotated[Optional[int], Field(alias='billing_interval_count')]
    ]
    billing_type: Annotated[str, Field(alias='billing_type')]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    default_stripe_coupon_id: NotRequired[
        Annotated[Optional[str], Field(alias='default_stripe_coupon_id')]
    ]
    description: NotRequired[Annotated[Optional[str], Field(alias='description')]]
    feature_set: NotRequired[Annotated[List[str], Field(alias='feature_set')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    key: Annotated[str, Field(alias='key')]
    name: NotRequired[Annotated[Optional[str], Field(alias='name')]]
    override_stripe_coupon_id: NotRequired[
        Annotated[Optional[str], Field(alias='override_stripe_coupon_id')]
    ]
    plan_family: NotRequired[Annotated[Optional[str], Field(alias='plan_family')]]
    rank: NotRequired[Annotated[Optional[int], Field(alias='rank')]]
    stripe_price_id: Annotated[str, Field(alias='stripe_price_id')]
    stripe_product_id: Annotated[str, Field(alias='stripe_product_id')]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]


class PublicStripeCatalogItemsUpdate(TypedDict):
    additional_data: NotRequired[Annotated[dict[str, Any], Field(alias='additional_data')]]
    archived: NotRequired[Annotated[bool, Field(alias='archived')]]
    billing_interval: NotRequired[Annotated[Optional[str], Field(alias='billing_interval')]]
    billing_interval_count: NotRequired[
        Annotated[Optional[int], Field(alias='billing_interval_count')]
    ]
    billing_type: NotRequired[Annotated[str, Field(alias='billing_type')]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    default_stripe_coupon_id: NotRequired[
        Annotated[Optional[str], Field(alias='default_stripe_coupon_id')]
    ]
    description: NotRequired[Annotated[Optional[str], Field(alias='description')]]
    feature_set: NotRequired[Annotated[List[str], Field(alias='feature_set')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    key: NotRequired[Annotated[str, Field(alias='key')]]
    name: NotRequired[Annotated[Optional[str], Field(alias='name')]]
    override_stripe_coupon_id: NotRequired[
        Annotated[Optional[str], Field(alias='override_stripe_coupon_id')]
    ]
    plan_family: NotRequired[Annotated[Optional[str], Field(alias='plan_family')]]
    rank: NotRequired[Annotated[Optional[int], Field(alias='rank')]]
    stripe_price_id: NotRequired[Annotated[str, Field(alias='stripe_price_id')]]
    stripe_product_id: NotRequired[Annotated[str, Field(alias='stripe_product_id')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]


class PublicJobs(BaseModel):
    created_at: datetime.datetime = Field(alias='created_at')
    data: dict[str, Any] = Field(alias='data')
    external_id: Optional[str] = Field(alias='external_id')
    finished_at: Optional[datetime.datetime] = Field(alias='finished_at')
    id: uuid.UUID = Field(alias='id')
    organization_id: uuid.UUID = Field(alias='organization_id')
    status: str = Field(alias='status')
    submitted_at: datetime.datetime = Field(alias='submitted_at')
    task: str = Field(alias='task')
    updated_at: Optional[datetime.datetime] = Field(alias='updated_at')
    user_id: uuid.UUID = Field(alias='user_id')


class PublicJobsInsert(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    data: NotRequired[Annotated[dict[str, Any], Field(alias='data')]]
    external_id: NotRequired[Annotated[Optional[str], Field(alias='external_id')]]
    finished_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='finished_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    organization_id: Annotated[uuid.UUID, Field(alias='organization_id')]
    status: NotRequired[Annotated[str, Field(alias='status')]]
    submitted_at: NotRequired[Annotated[datetime.datetime, Field(alias='submitted_at')]]
    task: Annotated[str, Field(alias='task')]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]
    user_id: Annotated[uuid.UUID, Field(alias='user_id')]


class PublicJobsUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias='created_at')]]
    data: NotRequired[Annotated[dict[str, Any], Field(alias='data')]]
    external_id: NotRequired[Annotated[Optional[str], Field(alias='external_id')]]
    finished_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='finished_at')]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias='id')]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias='organization_id')]]
    status: NotRequired[Annotated[str, Field(alias='status')]]
    submitted_at: NotRequired[Annotated[datetime.datetime, Field(alias='submitted_at')]]
    task: NotRequired[Annotated[str, Field(alias='task')]]
    updated_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias='updated_at')]]
    user_id: NotRequired[Annotated[uuid.UUID, Field(alias='user_id')]]
