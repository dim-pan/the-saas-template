import logging

from pydantic import BaseModel

from engine.gateway.processors.BaseWebhookProcessor import BaseWebhookProcessor
from engine.shared import api
from engine.shared.schemas import TaskStatus, WebhookContext

logger = logging.getLogger(__name__)


class JobDonePayload(BaseModel):
    """Payload when a task reports job completion (worker -> gateway -> backend)."""

    id: str


class ExampleWebhookProcessor(BaseWebhookProcessor):
    processor_name = 'example_task_1'
    payload_model = JobDonePayload

    @classmethod
    def can_process(cls, context: WebhookContext) -> bool:
        webhook_provider = context.headers.get('x-webhook-provider')
        return webhook_provider is not None and webhook_provider.lower() == cls.processor_name

    async def execute(self, context: WebhookContext, payload: JobDonePayload) -> dict[str, str]:
        logger.info(
            'Processed example webhook provider=%s job_id=%s',
            context.headers.get('x-webhook-provider'),
            payload.id,
        )

        job = await api.get_job_by_external_id(payload.id)
        if job is None:
            raise ValueError(f'No job found with external_id={payload.id}')

        # This is where we might do something like watermarking an image
        # or whatever. The idea is we take this super ugly and complex
        # external webhook and extract whatever we need and make it a lot
        # cleaner to pass back to the backend to finish the job.

        # For this example, we'll just return the job id

        await api.update_job_status(job.id, job.organization_id, TaskStatus.COMPLETED)

        return {'message': 'Job marked done'}
