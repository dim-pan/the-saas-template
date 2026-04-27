from app.database.handler import DatabaseHandler, Filter
from app.database.types_autogen import (
    PublicStripeCatalogItems,
    PublicStripeCatalogItemsInsert,
    PublicStripeCatalogItemsUpdate,
)
from app.utils.logger import get_logger
from supabase import Client

logger = get_logger(__name__)


class StripeCatalogItemsHandler(
    DatabaseHandler[
        PublicStripeCatalogItems,
        PublicStripeCatalogItemsInsert,
        PublicStripeCatalogItemsUpdate,
    ]
):
    def __init__(self, client: Client) -> None:
        super().__init__(client, table='stripe_catalog_items', row_model=PublicStripeCatalogItems)

    def list_catalog_items(
        self,
        *,
        billing_type: str | None = None,
        limit: int = 500,
    ) -> list[PublicStripeCatalogItems]:
        filters: list[Filter] = []
        if billing_type is not None:
            filters.append(Filter(column='billing_type', op='eq', value=billing_type))

        if billing_type == 'subscription':
            order_by = 'rank'
            ascending = True
        else:
            order_by = 'created_at'
            ascending = False

        return self.list_items(
            filters=filters,
            order_by=order_by,
            ascending=ascending,
            limit=limit,
        )

    def get_by_key(self, key: str) -> PublicStripeCatalogItems | None:
        key_trimmed = key.strip()
        if key_trimmed == '':
            return None

        rows = self.list_items(
            filters=[Filter(column='key', op='eq', value=key_trimmed)],
            limit=2,
            order_by='created_at',
            ascending=False,
        )
        if len(rows) == 0:
            return None
        if len(rows) > 1:
            logger.warning(
                'stripe_catalog_items.get_by_key returned multiple rows for key=%s (expected unique)',
                key_trimmed,
            )
        return rows[0]

    def get_by_stripe_price_id(self, stripe_price_id: str) -> PublicStripeCatalogItems | None:
        stripe_price_id_trimmed = stripe_price_id.strip()
        if stripe_price_id_trimmed == '':
            return None

        rows = self.list_items(
            filters=[Filter(column='stripe_price_id', op='eq', value=stripe_price_id_trimmed)],
            limit=2,
            order_by='created_at',
            ascending=False,
        )
        if len(rows) == 0:
            return None
        if len(rows) > 1:
            logger.warning(
                'stripe_catalog_items.get_by_stripe_price_id returned multiple rows for stripe_price_id=%s',
                stripe_price_id_trimmed,
            )
        return rows[0]

    def get_by_stripe_product_id(self, stripe_product_id: str) -> PublicStripeCatalogItems | None:
        stripe_product_id_trimmed = stripe_product_id.strip()
        if stripe_product_id_trimmed == '':
            return None

        rows = self.list_items(
            filters=[Filter(column='stripe_product_id', op='eq', value=stripe_product_id_trimmed)],
            limit=2,
            order_by='created_at',
            ascending=False,
        )
        if len(rows) == 0:
            return None
        if len(rows) > 1:
            logger.warning(
                'stripe_catalog_items.get_by_stripe_product_id returned multiple rows for stripe_product_id=%s',
                stripe_product_id_trimmed,
            )
        return rows[0]
