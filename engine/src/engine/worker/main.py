import asyncio
import logging

from pydantic import ValidationError

from engine.shared import api
from engine.shared.config import (
    AWS_SQS_QUEUE_URL,
    LOG_LEVEL,
)
from engine.shared.schemas import JobMessage, TaskStatus
from engine.worker.clients.sqs import SQSConnector
from engine.worker.processors import BaseProcessor, register_processors

logger = logging.getLogger(__name__)

WORKER_CONCURRENCY = 100


def parse_worker_message(raw_body: str | None) -> JobMessage | None:
    try:
        if not raw_body:
            raise ValidationError('Raw body is required')

        return JobMessage.model_validate_json(raw_body)
    except ValidationError as error:
        # TODO: Ensure this is reported to Sentry
        logger.error('Invalid worker message payload: %s', error)
        return None


def process_in_thread(msg: JobMessage) -> None:
    """Run the job in a dedicated thread with its own event loop (for asyncio.to_thread)."""
    thread_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(thread_loop)
    try:
        processor = BaseProcessor.get_processor(msg.task)
        thread_loop.run_until_complete(processor.process(msg))
    finally:
        thread_loop.close()


async def run_processor(msg: JobMessage, semaphore: asyncio.Semaphore) -> None:
    async with semaphore:
        try:
            await asyncio.to_thread(process_in_thread, msg)
        except Exception as error:
            logger.error('Error processing task %s: %s', msg.id, error)


async def main():
    queue_url = AWS_SQS_QUEUE_URL
    if queue_url is None:
        raise SystemExit(
            'AWS_SQS_QUEUE_URL is required but not set. Set it in the environment or .env.'
        )

    logger.info('Starting engine...')
    register_processors()
    sqs = SQSConnector.get_client()
    loop = asyncio.get_event_loop()
    semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)

    logger.info('Polling SQS... (concurrency=%s)', WORKER_CONCURRENCY)
    while True:
        # Blocking boto3 call in executor so event loop can run processor tasks
        response = await loop.run_in_executor(
            None,
            lambda: sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                VisibilityTimeout=30,
            ),
        )

        messages = response.get('Messages', [])
        if not messages:
            continue

        for message in messages:
            body = message.get('Body')

            receipt_handle = message.get('ReceiptHandle')
            assert receipt_handle is not None, (
                'AWS SQS guarantees a ReceiptHandle for every message so we just wanna silence the type checker'
            )

            validated_message = parse_worker_message(body)

            if validated_message is None:
                logger.error('Deleting invalid worker message payload: %s', body)
                # Invalid payload: delete so it doesn't retry infinitely (poison).
                await loop.run_in_executor(
                    None,
                    lambda rh=receipt_handle: sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=rh,
                    ),
                )
                continue

            logger.debug(
                'Validated task message id=%s status=%s task=%s',
                validated_message.id,
                validated_message.status,
                validated_message.task,
            )

            try:
                await api.update_job_status(
                    validated_message.id,
                    validated_message.organization_id,
                    TaskStatus.PROCESSING,
                )

                logger.info(
                    'Updated job status %s: %s', validated_message.id, TaskStatus.PROCESSING
                )
            except Exception as error:
                logger.error('Error updating job status %s: %s', validated_message.id, error)
                continue

            # Once the job status is updated, delete the message from the queue.
            await loop.run_in_executor(
                None,
                lambda rh=receipt_handle: sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=rh,
                ),
            )
            asyncio.create_task(run_processor(validated_message, semaphore))


if __name__ == '__main__':
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    asyncio.run(main())
