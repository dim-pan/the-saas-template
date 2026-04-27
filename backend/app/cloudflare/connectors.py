import hashlib
import hmac
import json
import time
from enum import Enum
from functools import lru_cache
from collections.abc import Sequence
from typing import Any, Literal, Self, TypedDict
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import boto3
import httpx
from mypy_boto3_s3.client import S3Client

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CFImageUploadResult(TypedDict, total=False):
    variants: list[str]


class AssetProvider(str, Enum):
    """Supported storage/upload providers for assets. Used for validation and API responses."""

    R2 = 'r2'
    IMAGE = 'image'
    STREAM = 'stream'


class ImageVariant(str, Enum):
    W400 = 'w400'
    H400 = 'h400'
    ORIGINAL = 'original'
    PUBLIC = 'public'
    THUMBNAIL = 'thumbnail'


def _mime_to_connector_key(mime_type: str) -> AssetProvider:
    """Map MIME type to the provider (connector key). Uses AssetProvider for a single source of truth."""
    if mime_type.startswith('image/'):
        return AssetProvider.IMAGE
    if mime_type.startswith('video/'):
        return AssetProvider.STREAM
    return AssetProvider.R2


def _filter_string_items(values: Sequence[object]) -> list[str]:
    return [item for item in values if isinstance(item, str)]


class CloudflareConnector:
    """Base class for all Cloudflare connectors.
    Handles the singleton pattern.
    """

    _is_initialized: bool

    @classmethod
    @lru_cache(maxsize=1)
    def _get_singleton(cls: type[Self]) -> Self:
        instance = super().__new__(cls)
        instance._is_initialized = False
        return instance

    def generate_presigned_url(
        self,
        action: Literal['put_object', 'get_object'],
        mime_type: str,
        key: str = '',
        expires_in: int = 3600,
    ) -> str:
        return ''

    def asset_exists(self, key: str) -> bool:
        return False

    def get_variant_url(self, storage_key: str, variant: 'ImageVariant') -> str:
        return ''

    def get_provider(self) -> AssetProvider:
        """Return the provider for this connector. Base implementation is unused in practice."""
        raise NotImplementedError('Subclass must implement get_provider')


class CFR2Connector(CloudflareConnector):
    def __new__(
        cls,
        account_id: str,
        access_key: str,
        secret_access_key: str,
        bucket: str = '',
    ) -> 'CFR2Connector':
        # Params are only used by __init__; required so constructor can receive them.
        _ = (account_id, access_key, secret_access_key, bucket)
        return cls._get_singleton()

    def __init__(
        self,
        account_id: str,
        access_key: str,
        secret_access_key: str,
        bucket: str = '',
    ) -> None:
        if self._is_initialized:
            return

        self.account_id = account_id
        self.access_key = access_key
        self.secret_access_key = secret_access_key
        self.bucket = bucket
        self._s3_client: S3Client = boto3.client(
            service_name='s3',
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_access_key,
            region_name='auto',
        )
        self._is_initialized = True

    @property
    def s3_client(self) -> S3Client:
        return self._s3_client

    def generate_presigned_url(
        self,
        action: Literal['put_object', 'get_object'],
        mime_type: str,
        key: str = '',
        expires_in: int = 3600,
    ) -> str:
        if not self.bucket or not key:
            return ''

        params: dict[str, str] = {'Bucket': self.bucket, 'Key': key}
        if action == 'put_object':
            params['ContentType'] = mime_type

        url = self._s3_client.generate_presigned_url(
            action,
            Params=params,
            ExpiresIn=expires_in,
        )

        return url or ''

    def asset_exists(self, key: str) -> bool:
        return self._s3_client.head_object(Bucket=self.bucket, Key=key) is not None

    def get_provider(self) -> AssetProvider:
        return AssetProvider.R2


class CFImageConnector(CloudflareConnector):
    DIRECT_UPLOAD_URL_TEMPLATE = (
        'https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v2/direct_upload'
    )
    LIST_IMAGES_URL_TEMPLATE = (
        'https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v2'
    )
    UPLOAD_IMAGE_URL_TEMPLATE = (
        'https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1'
    )

    def __new__(cls, account_id: str, api_token: str, signing_key: str = '') -> 'CFImageConnector':
        _ = (account_id, api_token, signing_key)
        return cls._get_singleton()

    def __init__(self, account_id: str, api_token: str, signing_key: str = '') -> None:
        if self._is_initialized:
            return

        self.account_id = account_id
        self.api_token = api_token
        self.signing_key = signing_key
        self._is_initialized = True

    def generate_presigned_url(
        self,
        action: Literal['put_object', 'get_object'],
        mime_type: str,
        key: str = '',
        expires_in: int = 3600,
    ) -> str:
        """put_object: one-time upload URL from Cloudflare Images direct_upload. get_object: signed variant URL."""
        if not self.account_id or not self.api_token:
            return ''

        match action:
            case 'get_object':
                if not key:
                    return ''
                variant_url = self.get_variant_url(key, ImageVariant.ORIGINAL)
                if not variant_url:
                    return ''
                return self._sign_image_url(variant_url, expires_in=expires_in)

            case 'put_object':
                url = self.DIRECT_UPLOAD_URL_TEMPLATE.format(account_id=self.account_id)
                headers = {'Authorization': f'Bearer {self.api_token}'}

                # Cloudflare expects multipart/form-data (curl --form), not urlencoded.
                files = {'requireSignedURLs': (None, 'true')}
                if key:
                    files['metadata'] = (None, json.dumps({'storage_key': key}))

                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, headers=headers, files=files)

                response.raise_for_status()
                body: dict[str, Any] = response.json()

                if not body.get('success'):
                    errors = body.get('errors', [])
                    logger.error('Cloudflare Images direct_upload failed: %s', errors)
                    return ''

                result = body.get('result') or {}
                upload_url = result.get('uploadURL') or ''

                if not upload_url or not isinstance(upload_url, str):
                    logger.error(
                        'Cloudflare Images direct_upload response missing uploadURL: %s',
                        body,
                    )
                    raise ValueError('Cloudflare Images direct_upload response missing uploadURL')

                return upload_url

    def get_variants_by_storage_key(self, storage_key: str) -> list[str]:
        if not self.account_id or not self.api_token:
            return []

        # List the image variants by storage key.
        url = self.LIST_IMAGES_URL_TEMPLATE.format(account_id=self.account_id)
        headers = {'Authorization': f'Bearer {self.api_token}'}
        params = {'meta.storage_key[eq]': storage_key, 'per_page': 1}

        with httpx.Client(timeout=60.0) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            body: dict[str, Any] = response.json()

        if not body.get('success'):
            logger.error('Cloudflare Images list failed: %s', body.get('errors'))
            return []

        images = (body.get('result') or {}).get('images') or []
        if not images:
            return []

        variants = images[0].get('variants') or []
        return [variant for variant in variants if variant]

    def get_variant_url(self, storage_key: str, variant: ImageVariant) -> str:
        """Get the URL for a variant of an image.

        Args:
            storage_key (str): The storage key of the image.
            variant (ImageVariant): The variant of the image.

        Returns:
            str: The URL for the variant of the image.
        """
        variants = self.get_variants_by_storage_key(storage_key)
        if not variants:
            return ''

        for variant_url in variants:
            if variant_url.endswith(f'/{variant.value}'):
                return variant_url

        base_variant_url = variants[0].rstrip('/')
        parts = base_variant_url.split('/')
        if len(parts) < 2:
            return ''
        return '/'.join(parts[:-1] + [variant.value])

    def _sign_image_url(self, url: str, *, expires_in: int) -> str:
        parsed_url = urlparse(url)
        query_items: list[tuple[str, str]] = parse_qsl(
            parsed_url.query,
            keep_blank_values=True,
        )
        expires_at = int(time.time()) + expires_in
        query_items.append(('exp', str(expires_at)))
        string_to_sign = f'{parsed_url.path}?{urlencode(query_items)}'
        signature = hmac.new(
            self.signing_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        query_items.append(('sig', signature))
        return urlunparse(parsed_url._replace(query=urlencode(query_items)))

    def get_private_image(self, storage_key: str, *, variant: ImageVariant) -> bytes:
        url = self.get_variant_url(storage_key, variant)

        with httpx.Client(timeout=60.0) as client:
            # Sign the URL to allow private access.
            parsed_url = urlparse(url)
            query_items = parse_qsl(parsed_url.query, keep_blank_values=True)
            expires_at = int(time.time()) + 60 * 5  # 5 minutes
            query_items.append(('exp', str(expires_at)))
            string_to_sign = f'{parsed_url.path}?{urlencode(query_items)}'
            # Generate the signature.
            signature = hmac.new(
                self.signing_key.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()
            query_items.append(('sig', signature))
            # Create the signed URL.
            signed_url = urlunparse(parsed_url._replace(query=urlencode(query_items)))
            # Fetch the private image.
            response = client.get(signed_url)

            response.raise_for_status()
            return response.content

    def upload_public_image(
        self,
        image_bytes: bytes,
        *,
        filename: str,
    ) -> CFImageUploadResult:
        if not self.account_id or not self.api_token:
            return {}

        url = self.UPLOAD_IMAGE_URL_TEMPLATE.format(account_id=self.account_id)
        headers = {'Authorization': f'Bearer {self.api_token}'}
        files = {
            'file': (filename, image_bytes),
            'requireSignedURLs': (None, 'false'),
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, files=files)

        response.raise_for_status()
        body: dict[str, object] = response.json()
        result = body.get('result')
        result_keys = list(result.keys()) if isinstance(result, dict) else []

        logger.info(
            'Cloudflare Images upload response: %s',
            {
                'status_code': response.status_code,
                'success': body.get('success'),
                'errors': body.get('errors'),
                'result_keys': result_keys,
            },
        )

        if not body.get('success'):
            logger.error('Cloudflare Images upload failed: %s', body.get('errors'))
            return {}

        if not isinstance(result, dict):
            return {}
        variants_value = result.get('variants')
        if not isinstance(variants_value, list):
            return {}
        variant_urls = _filter_string_items(variants_value)
        if len(variant_urls) == 0:
            return {}
        return {'variants': variant_urls}

    def get_provider(self) -> AssetProvider:
        return AssetProvider.IMAGE


class CFStreamConnector(CloudflareConnector):
    DIRECT_UPLOAD_URL_TEMPLATE = (
        'https://api.cloudflare.com/client/v4/accounts/{account_id}/stream/direct_upload'
    )
    SIGNED_TOKEN_URL_TEMPLATE = (
        'https://api.cloudflare.com/client/v4/accounts/{account_id}/stream/{video_uid}/token'
    )

    def __new__(
        cls,
        account_id: str,
        api_token: str,
        customer_subdomain: str = '',
    ) -> 'CFStreamConnector':
        _ = (account_id, api_token, customer_subdomain)
        return cls._get_singleton()

    def __init__(
        self,
        account_id: str,
        api_token: str,
        customer_subdomain: str = '',
    ) -> None:
        if self._is_initialized:
            return

        self.account_id = account_id
        self.api_token = api_token
        self.customer_subdomain = customer_subdomain
        self._is_initialized = True

    def generate_presigned_url(
        self,
        action: Literal['put_object', 'get_object'],
        mime_type: str,
        key: str = '',
        expires_in: int = 3600,
    ) -> str:
        if not self.account_id or not self.api_token:
            return ''

        match action:
            case 'get_object':
                if not self.customer_subdomain or not key:
                    return ''
                token = self.create_signed_token(key, expires_in=expires_in)
                if not token:
                    return ''
                return f'https://{self.customer_subdomain}/{token}/iframe'
            case 'put_object':
                upload_url, _ = self.create_direct_upload(expires_in=expires_in)
                return upload_url

    def create_direct_upload(
        self,
        *,
        expires_in: int = 3600,
        require_signed_urls: bool = True,
    ) -> tuple[str, str]:
        if not self.account_id or not self.api_token:
            return ('', '')

        url = self.DIRECT_UPLOAD_URL_TEMPLATE.format(account_id=self.account_id)
        headers = {'Authorization': f'Bearer {self.api_token}'}
        payload = {
            'maxDurationSeconds': expires_in,
            'requireSignedURLs': require_signed_urls,
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)

        response.raise_for_status()
        body: dict[str, Any] = response.json()
        if not body.get('success'):
            errors = body.get('errors', [])
            logger.error('Cloudflare Stream direct_upload failed: %s', errors)
            return ('', '')

        result = body.get('result') or {}
        upload_url = result.get('uploadURL') or ''
        video_uid = result.get('uid') or ''
        return (upload_url, video_uid)

    def create_signed_token(self, video_uid: str, *, expires_in: int | None = None) -> str:
        if not self.account_id or not self.api_token:
            return ''

        url = self.SIGNED_TOKEN_URL_TEMPLATE.format(
            account_id=self.account_id,
            video_uid=video_uid,
        )
        headers = {'Authorization': f'Bearer {self.api_token}'}

        payload: dict[str, int] | None = None
        if expires_in is not None:
            expires_at = int(time.time()) + expires_in
            payload = {'exp': expires_at}

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)

        response.raise_for_status()
        body: dict[str, Any] = response.json()
        if not body.get('success'):
            errors = body.get('errors', [])
            logger.error('Cloudflare Stream token failed: %s', errors)
            return ''

        result = body.get('result') or {}
        token = result.get('token') or ''
        return token

    def get_thumbnail_image(
        self,
        video_uid: str,
        *,
        time_offset: str = '0s',
        width: int | None = 711,
        height: int | None = None,
        fit: str | None = None,
    ) -> bytes:
        if not self.customer_subdomain:
            logger.error('Cloudflare Stream customer subdomain missing for thumbnails.')
            return b''

        token = self.create_signed_token(video_uid)
        if not token:
            return b''

        base_url = f'https://{self.customer_subdomain}'
        query_params: dict[str, str] = {'time': time_offset}
        if width is not None:
            query_params['width'] = str(width)
        if height is not None:
            query_params['height'] = str(height)
        if fit is not None:
            query_params['fit'] = fit
        query_string = urlencode(query_params)
        thumbnail_url = f'{base_url}/{token}/thumbnails/thumbnail.jpg?{query_string}'

        with httpx.Client(timeout=30.0) as client:
            response = client.get(thumbnail_url)
            response.raise_for_status()
            logger.info(
                'Cloudflare Stream thumbnail response: %s',
                {
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type'),
                    'content_length': response.headers.get('content-length'),
                    'url': str(response.request.url),
                },
            )
            return response.content

    def get_provider(self) -> AssetProvider:
        return AssetProvider.STREAM


CONNECTORS: dict[AssetProvider, type[CloudflareConnector]] = {
    AssetProvider.IMAGE: CFImageConnector,
    AssetProvider.STREAM: CFStreamConnector,
    AssetProvider.R2: CFR2Connector,
}

CONNECTOR_KWARGS: dict[AssetProvider, tuple[str, ...]] = {
    AssetProvider.IMAGE: ('account_id', 'api_token', 'signing_key'),
    AssetProvider.STREAM: ('account_id', 'api_token', 'customer_subdomain'),
    AssetProvider.R2: ('account_id', 'access_key', 'secret_access_key', 'bucket'),
}


def get_connector_for_upload(mime_type: str, **config: str) -> CloudflareConnector:
    """Get a connector for a given MIME type.

    Args:
        mime_type (str): The MIME type of the asset.
        **config: Additional configuration for the connector.

    Returns:
        CloudflareConnector: The connector for the given MIME type.
    """
    provider = _mime_to_connector_key(mime_type)
    cls = CONNECTORS[provider]
    kwargs_keys = CONNECTOR_KWARGS[provider]
    kwargs = {k: config.get(k, '') for k in kwargs_keys}
    logger.info(f'Getting connector for MIME type {mime_type} with kwargs {kwargs}.')
    return cls(**kwargs)
