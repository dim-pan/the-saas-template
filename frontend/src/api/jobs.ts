import { z } from 'zod';

import { apiGet, apiPost } from '@/api/client';
import {
  CreateJobRequestSchema,
  JobSchema,
  type CreateJobRequest,
} from '@/api/schemas/jobs';

const jobsListSchema = z.array(JobSchema);

export async function createJob(
  organizationId: string,
  payload: CreateJobRequest,
) {
  const orgId = z.uuid().parse(organizationId);
  const body = CreateJobRequestSchema.parse(payload);
  return apiPost(`/api/v1/org/${orgId}/jobs`, { body }, JobSchema);
}

export async function listJobs(organizationId: string) {
  const orgId = z.uuid().parse(organizationId);
  return apiGet(`/api/v1/org/${orgId}/jobs`, {}, jobsListSchema);
}

export async function getJob(organizationId: string, jobId: string) {
  const orgId = z.uuid().parse(organizationId);
  const id = z.uuid().parse(jobId);
  return apiGet(`/api/v1/org/${orgId}/jobs/${id}`, {}, JobSchema);
}
