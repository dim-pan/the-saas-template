from datetime import datetime, timezone
from uuid import UUID

from app.database.handler import DatabaseHandler
from app.database.types_autogen import (
    PublicStripeWebhookEvents,
    PublicStripeWebhookEventsInsert,
    PublicStripeWebhookEventsUpdate,
)
from app.utils.logger import get_logger
from supabase import Client

logger = get_logger(__name__)


class StripeWebhookEventsHandler(
    DatabaseHandler[
        PublicStripeWebhookEvents,
        PublicStripeWebhookEventsInsert,
        PublicStripeWebhookEventsUpdate,
    ]
):
    def __init__(self, client: Client) -> None:
        super().__init__(
            client,
            table='stripe_webhook_events',
            row_model=PublicStripeWebhookEvents,
        )

    def get_by_stripe_event_id(self, stripe_event_id: str) -> PublicStripeWebhookEvents | None:
        if stripe_event_id.strip() == '':
            raise ValueError('stripe_event_id is required')

        # stripe_event_id has a unique index, but we still guard + warn to be safe.
        result = (
            self.client.table(self.table)
            .select('*')
            .eq('stripe_event_id', stripe_event_id)
            .limit(2)
            .execute()
        )
        data = result.data
        if isinstance(data, list):
            if len(data) == 0:
                return None
            if len(data) > 1:
                logger.warning(
                    '%s: multiple rows found for stripe_event_id=%s',
                    self.table,
                    stripe_event_id,
                )
            return self.row_model.model_validate(data[0])
        if isinstance(data, dict):
            return self.row_model.model_validate(data)
        return None

    def update_item_status(
        self,
        row_id: UUID,
        *,
        processing_error: str | None = None,
    ) -> PublicStripeWebhookEvents:
        """
        Single status update primitive for webhook ingestion:
        - Always sets processed_at=now()
        - If processing_error is provided, persists it; otherwise clears it.
        """
        processed_at = datetime.now(timezone.utc)
        payload: PublicStripeWebhookEventsUpdate = {
            'processed_at': processed_at,
            'processing_error': processing_error,
        }
        return self.update_item(row_id, payload)

    def update_organization_id(
        self,
        row_id: UUID,
        *,
        organization_id: UUID,
    ) -> PublicStripeWebhookEvents:
        return self.update_item(row_id, {'organization_id': organization_id})
