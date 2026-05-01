import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from engine.shared.config import BACKEND_SECRET, BACKEND_URL
from engine.shared.schemas import JobLookupResponse, TaskStatus

logger = logging.getLogger(__name__)

_TIMEOUT = 30
_HEADERS = {'X-API-Key': BACKEND_SECRET}


def _is_retriable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


def _log_before_retry(retry_state) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    sleep = getattr(retry_state.next_action, 'sleep', 0)
    logger.warning(
        'Retrying in %s s after attempt %s: %s',
        sleep,
        retry_state.attempt_number,
        exc,
    )


_backend_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception(_is_retriable),
    before_sleep=_log_before_retry,
    reraise=True,
)


@_backend_retry
async def update_job_status(job_id: str, organization_id: str, status: TaskStatus) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f'{BACKEND_URL}/api/v1/org/{organization_id}/jobs/{job_id}/status',
            json={
                'status': status.value,
                'organization_id': organization_id,
            },
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )

        response.raise_for_status()


@_backend_retry
async def update_job_external_id(job_id: str, organization_id: str, external_id: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f'{BACKEND_URL}/api/v1/org/{organization_id}/jobs/{job_id}',
            json={'external_id': external_id},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()


@_backend_retry
async def update_job_result_data(
    job_id: str,
    organization_id: str,
    result_data: dict[str, Any],
) -> None:
    """Store result data on the job row (used by the worker to record errors etc.)."""
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f'{BACKEND_URL}/api/v1/org/{organization_id}/jobs/{job_id}/result',
            json={'result_data': result_data},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()


async def get_job_by_external_id(external_id: str) -> JobLookupResponse | None:
    async with httpx.AsyncClient() as client:
        url = f'{BACKEND_URL}/api/v1/jobs/lookup/by-external-id/{external_id}'
        response = await client.get(
            url,
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return JobLookupResponse.model_validate(response.json())
