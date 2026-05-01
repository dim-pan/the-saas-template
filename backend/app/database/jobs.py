from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from supabase import Client

from app.database.handler import DatabaseHandler, utc_now_iso
from app.database.types_autogen import (
    PublicJobs,
    PublicJobsInsert,
    PublicJobsUpdate,
)


class TaskStatus(Enum):
    QUEUED = 'queued'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


TERMINAL_STATUSES = (TaskStatus.COMPLETED, TaskStatus.FAILED)


class JobsHandler(DatabaseHandler[PublicJobs, PublicJobsInsert, PublicJobsUpdate]):
    def __init__(self, client: Client, *, organization_id: UUID | None = None) -> None:
        super().__init__(
            client,
            table='jobs',
            row_model=PublicJobs,
            organization_id=organization_id,
        )

    def mark_job_completed(self, job_id: UUID) -> PublicJobs:
        now = utc_now_iso()
        return self.update_item(job_id, {'status': TaskStatus.COMPLETED.value, 'finished_at': now})

    def update_job_status(self, job_id: UUID, status: TaskStatus) -> PublicJobs:
        if status not in TaskStatus:
            raise ValueError(f'Invalid status: {status}')

        payload: PublicJobsUpdate = {'status': status.value}
        if status in TERMINAL_STATUSES:
            payload['finished_at'] = datetime.now(timezone.utc)

        return self.update_item(job_id, payload)

    def get_job_by_external_id(
        self, external_id: str | UUID, *, require_org: bool = True
    ) -> PublicJobs | None:
        """Look up a job by external_id. When require_org=True (default), org-scoped and raises 404 if not found. When require_org=False, global lookup and returns None if not found."""
        return self.get_item(external_id, key='external_id', require_org=require_org)

    def update_job_result_data(self, job_id: UUID, result_data: dict[str, Any]) -> PublicJobs:
        return self.update_item(job_id, {'result_data': result_data})
