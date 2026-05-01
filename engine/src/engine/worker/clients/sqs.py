import logging
import os

import boto3
import boto3.session
from mypy_boto3_sqs import SQSClient

from engine.shared.config import AWS_REGION

logger = logging.getLogger(__name__)


class SQSConnector:
    # https://docs.aws.amazon.com/code-library/latest/ug/python_3_sqs_code_examples.html
    # Per boto3 multithreading guidance, use one session + client per thread/poller:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html#multithreading-and-multiprocessing

    @classmethod
    def get_client(cls) -> SQSClient:
        """Get a new SQS client with a new session (safe for concurrent use).

        Each caller gets its own Session and client; do not share across threads.
        Honors AWS_ENDPOINT_URL when set (e.g. local ElasticMQ at http://localhost:9324).

        Returns:
            SQSClient: The SQS client.
        """
        endpoint_url = os.getenv('AWS_ENDPOINT_URL') or None
        session = boto3.session.Session()
        return session.client('sqs', region_name=AWS_REGION, endpoint_url=endpoint_url)
