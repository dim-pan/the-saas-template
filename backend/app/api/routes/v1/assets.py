import datetime
from enum import Enum
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from app.api.deps import get_cloudflare_connector, get_supabase_client
from app.api.org_deps import OrgRoleContext, require_org_role
from app.cloudflare.connectors import (
    CFImageConnector,
    CFStreamConnector,
    CloudflareConnector,
    ImageVariant,
    AssetProvider,
)
from app.database.assets import AssetsHandler
from app.database.memberships import MembershipRole
from app.database.types_autogen import PublicAssets
from app.utils.logger import get_logger

MAX_UPLOAD_SIZE_BYTES = 200 * 1024 * 1024  # 200MB
router = APIRouter(prefix='/org/{organization_id}/assets', tags=['assets'])

logger = get_logger(__name__)


class AssetStatus(str, Enum):
    PENDING = 'pending'
    UPLOADED = 'uploaded'
    FAILED = 'failed'

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return self.value


class AllowedMimeType(str, Enum):
    """Allowed MIME types for asset uploads. Use these instead of raw strings."""

    IMAGE_JPEG = 'image/jpeg'
    IMAGE_PNG = 'image/png'
    IMAGE_GIF = 'image/gif'
    IMAGE_WEBP = 'image/webp'
    IMAGE_AVIF = 'image/avif'
    IMAGE_HEIC = 'image/heic'
    IMAGE_HEIF = 'image/heif'
    IMAGE_SVG_XML = 'image/svg+xml'
    VIDEO_MP4 = 'video/mp4'
    VIDEO_QUICKTIME = 'video/quicktime'
    FILE_PDF = 'application/pdf'


ALLOWED_MIME_TYPES = [m.value for m in AllowedMimeType]


class BodyWithMimeType(BaseModel):
    """Request body shape that only requires mime_type. Used for connector dependency."""

    mime_type: str


class CreateUploadRequest(BodyWithMimeType):
    filename: str
    size_bytes: int


class CreateUploadResponse(BaseModel):
    upload_url: str
    asset_id: UUID
    provider: AssetProvider


class CompleteUploadRequest(BodyWithMimeType):
    asset_id: UUID


class CompleteUploadResponse(BaseModel):
    asset_id: UUID


class GetAssetResponse(BaseModel):
    url: str
    asset: PublicAssets


def get_cloudflare_connector_for_upload_body(
    body: BodyWithMimeType,
) -> CloudflareConnector:
    """Dependency: return the connector for the request body's MIME type."""
    return get_cloudflare_connector(body.mime_type)


@router.get('/', response_model=list[PublicAssets])
async def list_assets(
    organization_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> list[PublicAssets]:
    assets_handler = AssetsHandler(db, organization_id=organization_id)
    if ctx.principal.kind == 'service':
        assets = assets_handler.list_assets_in_org()
    else:
        if ctx.user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User required')
        assets = assets_handler.list_assets(user_id=ctx.user.id)
    return assets


@router.get('/{asset_id}', response_model=GetAssetResponse)
async def get_asset(
    organization_id: UUID,
    asset_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> GetAssetResponse:
    assets_handler = AssetsHandler(db, organization_id=organization_id)
    asset = assets_handler.get_by_asset_id(asset_id)

    if asset.deleted_at is not None or asset.status != AssetStatus.UPLOADED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found',
        )

    if ctx.principal.kind == 'user' and ctx.user is not None and asset.user_id != ctx.user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not allowed to access this asset',
        )

    conn = get_cloudflare_connector(asset.mime_type)
    url = conn.generate_presigned_url(
        action='get_object',
        mime_type=asset.mime_type,
        key=asset.storage_key,
    )

    return GetAssetResponse(url=url, asset=asset)


@router.post('/uploads', response_model=CreateUploadResponse)
async def create_upload(
    organization_id: UUID,
    body: CreateUploadRequest,
    conn: CloudflareConnector = Depends(get_cloudflare_connector_for_upload_body),
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> CreateUploadResponse:
    if ctx.user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User token required')
    logger.info(f'/uploads: creating upload for {organization_id=} {ctx.user.id=}')
    mime_type = body.mime_type
    size_bytes = body.size_bytes
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        logger.warning(f'/uploads: file size exceeds 200MB: {size_bytes}')
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail='File size exceeds 200MB limit',
        )

    if mime_type not in ALLOWED_MIME_TYPES:
        logger.error(f'/uploads: MIME type not allowed: {mime_type}')
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f'MIME type not allowed: {body.mime_type}',
        )

    asset_id = uuid4()
    logger.info(f'/uploads: creating pending asset for {asset_id=}')

    provider = conn.get_provider()
    upload_url = ''

    match provider:
        case AssetProvider.STREAM:
            if not isinstance(conn, CFStreamConnector):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Incorrect connector used for stream upload',
                )
            upload_url, video_uid = conn.create_direct_upload()
            if not upload_url or not video_uid:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Stream upload URL generation failed',
                )
            storage_key = video_uid
        case AssetProvider.R2:
            storage_key = f'{organization_id}/{ctx.user.id}/{asset_id}'
            logger.info(f'/uploads: generating presigned URL for {storage_key=}')
            upload_url = conn.generate_presigned_url(
                action='put_object',
                mime_type=mime_type,
                key=storage_key,
            )
            logger.info(f'/uploads: presigned URL generated for {storage_key=}')
        case AssetProvider.IMAGE:
            storage_key = f'{organization_id}/{ctx.user.id}/{asset_id}'
            logger.info(f'/uploads: generating presigned URL for {storage_key=}')
            upload_url = conn.generate_presigned_url(
                action='put_object',
                mime_type=mime_type,
                key=storage_key,
            )
            logger.info(f'/uploads: presigned URL generated for {storage_key=}')

    assets_handler = AssetsHandler(db, organization_id=organization_id)
    assets_handler.create_pending_asset(
        asset_id=asset_id,
        user_id=ctx.user.id,
        filename=body.filename,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
        provider=provider.value,
    )

    return CreateUploadResponse(
        upload_url=upload_url,
        asset_id=asset_id,
        provider=provider,
    )


@router.delete('/{asset_id}')
async def delete_asset(
    asset_id: UUID,
    organization_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> None:
    assets_handler = AssetsHandler(db, organization_id=organization_id)
    asset = assets_handler.get_by_asset_id(asset_id)

    if asset.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Insufficient permissions',
        )

    if asset.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found',
        )
    assets_handler.set_deleted(
        asset_id=asset_id,
        deleted_at=datetime.datetime.now(datetime.UTC),
    )
    logger.info(f'/assets/delete: marked as deleted for {asset_id=}')


@router.post('/uploads/{upload_id}/complete', response_model=CompleteUploadResponse)
async def complete_upload(
    organization_id: UUID,
    upload_id: UUID,
    body: CompleteUploadRequest,
    conn: CloudflareConnector = Depends(get_cloudflare_connector_for_upload_body),
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> CompleteUploadResponse:
    asset_id = body.asset_id
    if asset_id != upload_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Path upload_id must match body asset_id',
        )

    assets_handler = AssetsHandler(db, organization_id=organization_id)
    asset = assets_handler.get_by_asset_id(asset_id)
    try:
        provider = AssetProvider(asset.provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Invalid asset provider: {asset.provider!r}',
        )
    storage_key = asset.storage_key

    try:
        # 2. Different ways to handle the upload completion.
        match provider:
            case AssetProvider.R2:
                # With R2 we need to check if the asset exists before completing the upload.
                logger.info(f'/uploads/complete: checking if asset exists on R2: {asset_id=}')

                if not conn.asset_exists(storage_key):
                    logger.error('complete_upload: asset not found on R2: %s', storage_key)
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'Asset not found: {storage_key}',
                    )
            case AssetProvider.IMAGE:
                # Thumbnail fetching for images.
                if not isinstance(conn, CFImageConnector):
                    # Ensure we're using the correct connector.
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail='Incorrect connector used for image completion',
                    )

                # We just need to go fetch the thumbnail URL from Cloudflare.
                thumbnail_url = conn.get_variant_url(storage_key, ImageVariant.THUMBNAIL)
                if not thumbnail_url:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail='Cloudflare thumbnail URL missing',
                    )

                # Store the thumbnail URL in the database.
                logger.info(f'/uploads/complete: storing thumbnail URL for {asset_id=}')
                assets_handler.set_thumbnail(asset_id=asset_id, thumbnail_url=thumbnail_url)

            case AssetProvider.STREAM:
                # Thumbnail generation for videos using Cloudflare Stream.
                if not storage_key:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail='Asset storage_key missing',
                    )
                if not isinstance(conn, CFStreamConnector):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail='Incorrect connector used for stream completion',
                    )

                thumbnail_bytes = conn.get_thumbnail_image(
                    storage_key,
                    fit='crop',
                )
                if not thumbnail_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail='Stream thumbnail bytes missing',
                    )

                image_conn = get_cloudflare_connector(AllowedMimeType.IMAGE_JPEG.value)
                if not isinstance(image_conn, CFImageConnector):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail='Incorrect connector used for image upload',
                    )

                thumbnail_filename = f'{asset.filename.split(".")[0]}_thumb.jpg'
                public_result = image_conn.upload_public_image(
                    thumbnail_bytes,
                    filename=thumbnail_filename,
                )
                variants = public_result.get('variants') if public_result else None
                if not isinstance(variants, list):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail='Cloudflare public image variants missing',
                    )

                thumbnail_url = next(
                    (
                        variant_url
                        for variant_url in variants
                        if isinstance(variant_url, str) and variant_url.endswith('/public')
                    ),
                    None,
                )
                if thumbnail_url is None:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail='Cloudflare public thumbnail URL missing',
                    )

                logger.info(f'/uploads/complete: storing thumbnail URL for {asset_id=}')
                assets_handler.set_thumbnail(asset_id=asset_id, thumbnail_url=thumbnail_url)
    except HTTPException:
        assets_handler.set_failed(asset_id=asset_id)
        raise
    except Exception as error:
        assets_handler.set_failed(asset_id=asset_id)
        logger.exception('complete_upload: marking asset failed: %s', error)
        raise

    assets_handler.complete_upload(asset_id=asset_id)
    logger.info(f'/uploads/complete: completed upload for {asset_id=}')

    return CompleteUploadResponse(asset_id=asset_id)
