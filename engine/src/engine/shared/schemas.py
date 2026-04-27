from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class TaskStatus(Enum):
    QUEUED = 'queued'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


# This must be kept in sync with the jobs table in the backend
class JobMessage(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str
    external_id: str | None = None
    organization_id: str
    user_id: str
    status: TaskStatus
    task: str
    submitted_at: datetime
    updated_at: datetime
    created_at: datetime
    finished_at: datetime | None = None
    # TODO: each job should have a different data schema
    # We can use a union type to represent the different schemas
    data: dict[str, Any]


class WebhookContext(BaseModel):
    model_config = ConfigDict(extra='forbid')

    path: str
    method: str
    headers: dict[str, str]
    query_params: dict[str, str]
    raw_body: str
    body: dict[str, Any]
