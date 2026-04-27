import datetime
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.database.handler import DatabaseHandler, Filter
from app.database.types_autogen import (
    PublicAssets,
    PublicAssetsInsert,
    PublicAssetsUpdate,
)


class AssetsHandler(DatabaseHandler[PublicAssets, PublicAssetsInsert, PublicAssetsUpdate]):
    organization_id: UUID

    def __init__(self, client: Client, *, organization_id: UUID) -> None:
        super().__init__(
            client,
            table='assets',
            row_model=PublicAssets,
            organization_id=organization_id,
        )

    def get_by_asset_id(self, asset_id: UUID) -> PublicAssets:
        row = self.get_item(asset_id, key='asset_id', require_org=True)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
        return row

    def update_by_asset_id(self, asset_id: UUID, values: dict[str, object]) -> PublicAssets:
        return self.update_item(asset_id, values, key='asset_id')

    def create_pending_asset(
        self,
        asset_id: UUID,
        user_id: UUID,
        filename: str,
        storage_key: str,
        mime_type: str,
        size_bytes: int,
        provider: str,
    ) -> PublicAssets:
        payload: PublicAssetsInsert = {
            'asset_id': asset_id,
            'organization_id': self.organization_id,
            'user_id': user_id,
            'filename': filename,
            'storage_key': storage_key,
            'mime_type': mime_type,
            'size_bytes': size_bytes,
            'status': 'pending',
            'provider': provider,
        }
        return self.create_item(payload)

    def complete_upload(self, asset_id: UUID) -> PublicAssets:
        return self.update_by_asset_id(asset_id, {'status': 'uploaded'})

    def set_thumbnail(self, asset_id: UUID, thumbnail_url: str) -> PublicAssets:
        return self.update_by_asset_id(asset_id, {'thumbnail_url': thumbnail_url})

    def set_deleted(self, asset_id: UUID, deleted_at: datetime.datetime) -> PublicAssets:
        # TODO: this should be baked everywhere in the DatabaseHandler (base class), not in the subclasses
        return self.update_by_asset_id(asset_id, {'deleted_at': deleted_at})

    def set_failed(self, asset_id: UUID) -> PublicAssets:
        return self.update_by_asset_id(asset_id, {'status': 'failed'})

    def list_assets(self, user_id: UUID) -> list[PublicAssets]:
        filters = [
            Filter(column='deleted_at', op='is', value=None),
            Filter(column='user_id', op='eq', value=user_id),
        ]
        return self.list_items(filters=filters)

    def list_assets_in_org(self) -> list[PublicAssets]:
        """List all non-deleted assets in the org (no user filter). Used for service principal."""
        filters = [Filter(column='deleted_at', op='is', value=None)]
        return self.list_items(filters=filters)
