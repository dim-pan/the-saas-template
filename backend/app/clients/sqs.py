import logging
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_sqs.client import SQSClient
import uuid

from app.config import AWS_REGION

logger = logging.getLogger(__name__)


class SQSConnector:
    """Send messages to SQS only (no receive)."""

    @classmethod
    @lru_cache(maxsize=1)
    def get_client(cls) -> SQSClient:
        """Return a cached boto3 SQS client."""
        client: SQSClient = boto3.client(
            'sqs',
            region_name=AWS_REGION,
        )

        return client

    @classmethod
    def send_message(cls, queue_url: str, body: str) -> None:
        """
        Send a message to an SQS queue.

        Args:
            queue_url: The URL of the queue.
            body: The message body (string, typically JSON).

        Raises:
            ClientError: If sending fails.
        """
        client = cls.get_client()
        try:
            client.send_message(
                QueueUrl=queue_url,
                MessageBody=body,
                MessageDeduplicationId=str(uuid.uuid4()),
                MessageGroupId='engine',
            )
            logger.info('Sent message to queue %s', queue_url)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error('Error sending message to SQS: %s - %s', error_code, e)
            raise
