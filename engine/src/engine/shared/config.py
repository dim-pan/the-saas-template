# Centralized environment configuration.
# Keep this intentionally lightweight (simple constants) for now.
import logging
import os

logger = logging.getLogger(__name__)

ENV = os.getenv('ENV', 'dev')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


# AWS configuration
AWS_REGION = os.getenv('AWS_REGION')
AWS_SQS_QUEUE_URL = os.getenv('AWS_SQS_QUEUE_URL')

# Backend
BACKEND_URL = os.getenv('BACKEND_URL', '').rstrip('/')
BACKEND_SECRET = os.getenv('BACKEND_SECRET', '')
