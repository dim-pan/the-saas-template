import logging
import logging.config

from app.config import ENV, LOG_LEVEL


def configure_logging() -> None:
    """
    Central logging configuration entrypoint.

    Today: logs to stdout (good for local + Docker).
    Later: extend by adding additional handlers (e.g. file, OTLP, Datadog, etc.).
    Uses a single plain format (timestamp, level, name, message) for the app
    and for uvicorn so output is consistent and readable.
    """

    # Default to DEBUG in dev for better local diagnosability.
    # Production should explicitly set LOG_LEVEL=INFO (or higher).
    current_env = ENV
    default_level = 'DEBUG' if current_env == 'dev' else 'INFO'
    log_level = (LOG_LEVEL or default_level).upper()

    logging.config.dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format': '%(asctime)s %(levelname)-8s %(name)s %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S',
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'default',
                }
            },
            'root': {'level': log_level, 'handlers': ['console']},
            # Suppress noisy HTTP/2 debug logs from httpx/httpcore (Supabase client).
            'loggers': {
                'httpx': {'level': 'INFO'},
                'httpcore': {'level': 'INFO'},
                'hpack': {'level': 'INFO'},
            },
        }
    )

    # Force uvicorn loggers to use our format only (no duplicate handlers/boxes).
    for name in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
