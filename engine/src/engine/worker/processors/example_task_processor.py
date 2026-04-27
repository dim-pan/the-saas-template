import asyncio
import logging
import uuid

import httpx
from pydantic import BaseModel

from engine.shared import api
from engine.shared.schemas import JobMessage
from engine.worker.processors.BaseProcessor import BaseProcessor

logger = logging.getLogger(__name__)


class ExampleTaskData(BaseModel):
    name: str


class ExampleTaskProcessor(BaseProcessor):
    task_name = 'example_task_1'
    payload_model = ExampleTaskData

    async def execute(self, message: JobMessage, payload: ExampleTaskData) -> None:
        logger.info('Processing example task id=%s name=%s', message.id, payload.name)

        # Pretend we send a request to an external service like FAL or OpenAI
        res = {
            'id': f'ext-{uuid.uuid4()}',
        }
        external_id = res['id']

        # Update backend with new external_id (internal endpoint, requires X-API-Key)
        await api.update_job_external_id(message.id, message.organization_id, external_id)

        await asyncio.sleep(3)

        # This simulates the external service responding to the gateway.
        # This code would not be in the worker, but in the external service e.g. FAL or OpenAI.
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'http://localhost:8001/wh',
                headers={'x-webhook-provider': self.task_name},
                json={
                    'id': external_id,
                },
            )
            response.raise_for_status()

        logger.info('Finished processing example task id=%s', message.id)
