import { z } from 'zod';

import { apiGet, apiPatch } from '@/api/client';
import {
  OrganizationSchema,
  OrganizationUpdateRequestSchema,
} from '@/api/schemas/organizations';
import type { OrganizationUpdateRequest } from '@/api/schemas/organizations';

const uuidSchema = z.uuid();

const organizationsListSchema = z.array(OrganizationSchema);

export async function listOrganizations() {
  return apiGet('/api/v1/org', {}, organizationsListSchema);
}

export async function getOrganization(organizationId: string) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  return apiGet(`/api/v1/org/${parsedOrganizationId}`, {}, OrganizationSchema);
}

export async function updateOrganization(
  organizationId: string,
  payload: OrganizationUpdateRequest,
) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedPayload = OrganizationUpdateRequestSchema.parse(payload);
  return apiPatch(
    `/api/v1/org/${parsedOrganizationId}`,
    { body: parsedPayload },
    OrganizationSchema,
  );
}
