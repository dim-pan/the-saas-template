from collections.abc import Generator

from fastapi import HTTPException, Header, status
from supabase import Client

from app.cloudflare.connectors import CloudflareConnector, get_connector_for_upload
from app.config import (
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_ACCESS_KEY,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_IMAGES_SIGNING_KEY,
    CLOUDFLARE_R2_BUCKET,
    CLOUDFLARE_SECRET_ACCESS_KEY,
    CLOUDFLARE_STREAM_CUSTOMER_SUBDOMAIN,
    BACKEND_SECRET,
)
from app.database.client import get_database


def get_supabase_client() -> Generator[Client, None, None]:
    # Supabase client doesn't require explicit closing, but using a generator keeps the
    # dependency pattern consistent if we later switch to a closeable resource.
    yield get_database()


def get_cloudflare_connector(mime_type: str) -> CloudflareConnector:
    """Return the Cloudflare connector for the given MIME type."""
    return get_connector_for_upload(
        mime_type,
        account_id=CLOUDFLARE_ACCOUNT_ID,
        api_token=CLOUDFLARE_API_TOKEN,
        signing_key=CLOUDFLARE_IMAGES_SIGNING_KEY,
        access_key=CLOUDFLARE_ACCESS_KEY,
        secret_access_key=CLOUDFLARE_SECRET_ACCESS_KEY,
        bucket=CLOUDFLARE_R2_BUCKET,
        customer_subdomain=CLOUDFLARE_STREAM_CUSTOMER_SUBDOMAIN,
    )


def require_engine_secret(
    x_api_secret: str | None = Header(None, alias='X-API-Key'),
) -> None:
    if not BACKEND_SECRET or x_api_secret != BACKEND_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or missing secret'
        )
