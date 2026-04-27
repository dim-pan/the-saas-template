import httpx

from engine.shared.config import BACKEND_SECRET, BACKEND_URL
from engine.shared.schemas import JobMessage, TaskStatus

_TIMEOUT = 10
_HEADERS = {'X-API-Key': BACKEND_SECRET}


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


async def update_job_external_id(job_id: str, organization_id: str, external_id: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f'{BACKEND_URL}/api/v1/org/{organization_id}/jobs/{job_id}',
            json={'external_id': external_id},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()


async def get_job_by_external_id(external_id: str) -> JobMessage | None:
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
        return JobMessage.model_validate(response.json())
