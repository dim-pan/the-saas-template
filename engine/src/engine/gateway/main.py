import json
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from engine.gateway.logging_setup import configure_engine_logging
from engine.gateway.processors import BaseWebhookProcessor, register_processors
from engine.shared.schemas import WebhookContext

configure_engine_logging()

app = FastAPI(title='The Engine Gateway')
logger = logging.getLogger(__name__)
register_processors()


@app.post('/wh')
async def webhook(request: Request) -> dict[str, Any]:
    raw_body_bytes = await request.body()
    raw_body = raw_body_bytes.decode('utf-8')
    logger.info('Received webhook: %s', raw_body)

    # TODO: Set up schema routing instead of this manual parsing
    body: dict[str, Any] = {}
    if raw_body:
        try:
            parsed_body = json.loads(raw_body)
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=400, detail='Webhook body must be valid JSON'
            ) from error

        if not isinstance(parsed_body, dict):
            raise HTTPException(status_code=400, detail='Webhook body must be a JSON object')

        body = parsed_body

    logger.info('Parsed webhook body: %s', body)
    context = WebhookContext(
        path=request.url.path,
        method=request.method,
        headers={key.lower(): value for key, value in request.headers.items()},
        query_params={key: value for key, value in request.query_params.items()},
        raw_body=raw_body,
        body=body,
    )

    try:
        processor = BaseWebhookProcessor.get_processor(context)
        logger.info('Processor: %s', processor)
        return await processor.process(context)
    except ValueError as error:
        logger.warning('Webhook rejected (400): %s', error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception('Unexpected gateway error while processing webhook: %s', error)
        raise HTTPException(status_code=500, detail='Internal server error') from error
