import { z } from 'zod';

import { apiDelete, apiGet, apiPatch } from '@/api/client';
import {
  MembershipRoleUpdateSchema,
  MembershipSchema,
} from '@/api/schemas/memberships';
import type { UpdateMembershipRoleRequest } from '@/api/schemas/memberships';

const uuidSchema = z.uuid();

const membershipsListSchema = z.array(MembershipSchema);

export async function listOrgMemberships(organizationId: string) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  return apiGet(
    `/api/v1/org/${parsedOrganizationId}/memberships`,
    {},
    membershipsListSchema,
  );
}

export async function getMyMembership(organizationId: string) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  return apiGet(
    `/api/v1/org/${parsedOrganizationId}/membership`,
    {},
    MembershipSchema,
  );
}

export async function updateMembershipRole(
  organizationId: string,
  membershipId: string,
  payload: UpdateMembershipRoleRequest,
) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedMembershipId = uuidSchema.parse(membershipId);
  const parsedPayload = MembershipRoleUpdateSchema.parse(payload);
  return apiPatch(
    `/api/v1/org/${parsedOrganizationId}/memberships/${parsedMembershipId}`,
    { body: parsedPayload },
    MembershipSchema,
  );
}

export async function deleteMembership(
  organizationId: string,
  membershipId: string,
) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedMembershipId = uuidSchema.parse(membershipId);
  return apiDelete(
    `/api/v1/org/${parsedOrganizationId}/memberships/${parsedMembershipId}`,
    {},
    MembershipSchema,
  );
}
