import json
import urllib.error
import urllib.request
from typing import Any

from app.config import SLACK_PAYMENTS_WEBHOOK_URL
from app.utils.logger import get_logger

logger = get_logger(__name__)


def send_slack_payments_message(*, text: str, blocks: list[dict[str, Any]] | None = None) -> bool:
    """
    Send a message to the payments Slack webhook.

    Returns True if a request was sent successfully; False if webhook is not configured
    or the request failed.
    """
    webhook_url = SLACK_PAYMENTS_WEBHOOK_URL
    if webhook_url is None or webhook_url.strip() == '':
        logger.warning('slack payments webhook not configured (SLACK_PAYMENTS_WEBHOOK_URL)')
        return False

    payload: dict[str, Any] = {'text': text}
    if blocks is not None:
        payload['blocks'] = blocks

    body = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status_code = getattr(response, 'status', None)
            if status_code is not None and int(status_code) >= 400:
                logger.warning('slack payments webhook returned status=%s', status_code)
                return False
            return True
    except urllib.error.HTTPError as exc:
        logger.warning('slack payments webhook http error status=%s', getattr(exc, 'code', None))
        return False
    except Exception as exc:
        logger.warning('slack payments webhook request failed: %s', str(exc))
        return False
