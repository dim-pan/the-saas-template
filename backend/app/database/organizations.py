from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.database.handler import DatabaseHandler
from app.database.types_autogen import (
    PublicOrganizations,
    PublicOrganizationsInsert,
    PublicOrganizationsUpdate,
)
from app.utils.logger import get_logger
from supabase import Client

logger = get_logger(__name__)


class OrganizationsHandler(
    DatabaseHandler[
        PublicOrganizations,
        PublicOrganizationsInsert,
        PublicOrganizationsUpdate,
    ]
):
    def __init__(self, client: Client) -> None:
        super().__init__(client, table='organizations', row_model=PublicOrganizations)

    def set_stripe_customer(
        self,
        organization_id: UUID,
        *,
        stripe_customer_id: str,
        billing_email: str | None = None,
        additional_data: Mapping[str, Any] | None = None,
    ) -> PublicOrganizations:
        payload: PublicOrganizationsUpdate = {'stripe_customer_id': stripe_customer_id}
        if billing_email is not None:
            payload['billing_email'] = billing_email
        if additional_data is not None:
            payload['additional_data'] = dict(additional_data)
        return self.update_item(organization_id, payload)

    def get_by_stripe_customer_id(self, stripe_customer_id: str) -> PublicOrganizations | None:
        if stripe_customer_id.strip() == '':
            raise ValueError('stripe_customer_id is required')

        result = (
            self.client.table(self.table)
            .select('*')
            .eq('stripe_customer_id', stripe_customer_id)
            .limit(2)
            .execute()
        )
        data = result.data
        if isinstance(data, list):
            if len(data) == 0:
                return None
            if len(data) > 1:
                logger.warning(
                    '%s: multiple rows found for stripe_customer_id=%s',
                    self.table,
                    stripe_customer_id,
                )
            return self.row_model.model_validate(data[0])
        if isinstance(data, dict):
            return self.row_model.model_validate(data)
        return None
