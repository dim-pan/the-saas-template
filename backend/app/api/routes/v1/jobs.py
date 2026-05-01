import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, RootModel
from supabase import Client

from app.api.deps import get_supabase_client
from app.api.org_deps import OrgRoleContext, require_org_role
from app.auth.deps import Principal, require_role
from app.clients.sqs import SQSConnector
from app.config import AWS_SQS_QUEUE_URL
from app.database.jobs import JobsHandler, TaskStatus
from app.database.memberships import MembershipRole
from app.database.types_autogen import PublicJobs

logger = logging.getLogger(__name__)

org_level_router = APIRouter(
    prefix='/org/{organization_id}/jobs',
    tags=['jobs'],
)

router = APIRouter(
    prefix='/jobs',
    tags=['jobs'],
)


class UpdateJobExternalIdRequest(BaseModel):
    external_id: str


class UpdateJobStatusRequest(BaseModel):
    status: TaskStatus


class UpdateJobResultDataRequest(BaseModel):
    result_data: dict[str, Any]


class WorkerTaskMessagePayload(BaseModel):
    """Payload shape for SQS message body"""

    model_config = ConfigDict(extra='forbid')

    id: str
    organization_id: str
    user_id: str
    status: TaskStatus
    task: str
    submitted_at: datetime
    updated_at: datetime
    created_at: datetime
    finished_at: datetime | None = None
    data: dict[str, Any]


class JobResult(PublicJobs):
    pass


class JobListResult(RootModel[list[JobResult]]):
    pass


class CreateJobRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    task: str
    data: dict[str, object] = {}
    user_id: UUID | None = None  # required when using service account


@router.get(
    '/lookup/by-external-id/{external_id}',
    response_model=JobResult,
    summary='Look up a job by external ID',
)
def get_job_by_external_id(
    external_id: str,
    db: Client = Depends(get_supabase_client),
    _principal: Principal = Depends(require_role('member')),
) -> JobResult:
    """Read-only lookup by external_id. Returns 404 if not found."""
    jobs = JobsHandler(db, organization_id=None)
    row = jobs.get_job_by_external_id(external_id, require_org=False)
    if row is None:
        raise HTTPException(status_code=404, detail='Job not found')
    return JobResult.model_validate(row, from_attributes=True)


@org_level_router.post('/', response_model=JobResult)
def create_job(
    organization_id: UUID,
    payload: CreateJobRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> JobResult:
    if ctx.principal.kind == 'user':
        if ctx.user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User required')
        user_id = ctx.user.id
    else:
        if payload.user_id is None:
            raise HTTPException(
                status_code=400,
                detail='user_id is required when creating a job with a service account',
            )
        user_id = payload.user_id

    jobs = JobsHandler(db, organization_id=organization_id)
    row = jobs.create_item(
        {
            'organization_id': organization_id,
            'user_id': user_id,
            'task': payload.task,
            'data': payload.data,
        }
    )

    # Send to SQS (engine expects WorkerTaskMessage JSON body)
    if AWS_SQS_QUEUE_URL:
        try:
            logger.info('Sending job to SQS: %s', row)

            # Generate a WorkerTaskMessagePayload from the PublicJobs row to send to SQS
            worker_message = WorkerTaskMessagePayload(
                id=str(row.id),
                organization_id=str(row.organization_id),
                user_id=str(row.user_id),
                status=TaskStatus(row.status),
                task=row.task,
                submitted_at=row.submitted_at,
                updated_at=row.updated_at or row.submitted_at,
                created_at=row.created_at,
                finished_at=row.finished_at,
                data=dict(row.data),
            )

            body = worker_message.model_dump_json()

            SQSConnector.send_message(AWS_SQS_QUEUE_URL, body)
            logger.info('Job sent to SQS: %s', row)
        except Exception as e:
            logger.exception('Failed to send job to SQS: %s', e)
            raise

    return JobResult.model_validate(row, from_attributes=True)


@org_level_router.get('/', response_model=JobListResult)
def list_jobs(
    organization_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> JobListResult:
    jobs = JobsHandler(db, organization_id=organization_id)
    rows = jobs.list_items()
    return JobListResult.model_validate(
        [JobResult.model_validate(r, from_attributes=True) for r in rows]
    )


@org_level_router.get('/{job_id}', response_model=JobResult)
def get_job(
    organization_id: UUID,
    job_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> JobResult:
    jobs = JobsHandler(db, organization_id=organization_id)
    row = jobs.get_item(job_id)
    return JobResult.model_validate(row, from_attributes=True)


@org_level_router.patch('/{job_id}/status', response_model=JobResult)
def update_job_status(
    organization_id: UUID,
    job_id: UUID,
    payload: UpdateJobStatusRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> JobResult:
    jobs = JobsHandler(db, organization_id=organization_id)
    row = jobs.update_job_status(job_id, payload.status)
    return JobResult.model_validate(row, from_attributes=True)


@org_level_router.patch('/{job_id}', response_model=JobResult)
def update_job_external_id(
    organization_id: UUID,
    job_id: UUID,
    payload: UpdateJobExternalIdRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> JobResult:
    jobs = JobsHandler(db, organization_id=organization_id)
    row = jobs.update_item(job_id, {'external_id': payload.external_id})
    return JobResult.model_validate(row, from_attributes=True)


@org_level_router.patch('/{job_id}/result', response_model=JobResult)
def update_job_result_data(
    organization_id: UUID,
    job_id: UUID,
    payload: UpdateJobResultDataRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role(MembershipRole.member)),
) -> JobResult:
    jobs = JobsHandler(db, organization_id=organization_id)
    row = jobs.update_job_result_data(job_id, payload.result_data)
    return JobResult.model_validate(row, from_attributes=True)
