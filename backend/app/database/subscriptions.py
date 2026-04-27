from uuid import UUID

from app.database.handler import DatabaseHandler, Filter
from app.database.types_autogen import (
    PublicSubscriptions,
    PublicSubscriptionsInsert,
    PublicSubscriptionsUpdate,
)
from app.utils.logger import get_logger
from supabase import Client

logger = get_logger(__name__)


class SubscriptionsHandler(
    DatabaseHandler[
        PublicSubscriptions,
        PublicSubscriptionsInsert,
        PublicSubscriptionsUpdate,
    ]
):
    organization_id: UUID

    def __init__(self, client: Client, *, organization_id: UUID) -> None:
        super().__init__(
            client,
            table='subscriptions',
            row_model=PublicSubscriptions,
            organization_id=organization_id,
        )

    def get_by_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> PublicSubscriptions | None:
        trimmed = stripe_subscription_id.strip()
        if trimmed == '':
            return None

        rows = self.list_items(
            filters=[Filter(column='stripe_subscription_id', op='eq', value=trimmed)],
            limit=2,
            order_by='created_at',
            ascending=False,
        )
        if len(rows) == 0:
            return None
        if len(rows) > 1:
            logger.warning(
                '%s: multiple rows found for stripe_subscription_id=%s',
                self.table,
                trimmed,
            )
        return rows[0]
