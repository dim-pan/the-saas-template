import { z } from 'zod';
import { apiDelete, apiGet, apiPatch } from '@/api/client';
import { UserSchema, UserUpdateSchema } from '@/api/schemas/users';
import type { UpdateUserRequest } from '@/api/schemas/users';

const uuidSchema = z.uuid();

export async function getUser(organizationId: string, userId: string) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedUserId = uuidSchema.parse(userId);
  return apiGet(
    `/api/v1/org/${parsedOrganizationId}/users/${parsedUserId}`,
    {},
    UserSchema,
  );
}

export async function updateUser(
  organizationId: string,
  userId: string,
  payload: UpdateUserRequest,
) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedUserId = uuidSchema.parse(userId);
  const parsedPayload = UserUpdateSchema.parse(payload);
  return apiPatch(
    `/api/v1/org/${parsedOrganizationId}/users/${parsedUserId}`,
    { body: parsedPayload },
    UserSchema,
  );
}

export async function deleteUser(organizationId: string, userId: string) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedUserId = uuidSchema.parse(userId);
  return apiDelete(
    `/api/v1/org/${parsedOrganizationId}/users/${parsedUserId}`,
    {},
    UserSchema,
  );
}
