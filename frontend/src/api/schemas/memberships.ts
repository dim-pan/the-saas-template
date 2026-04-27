import { z } from 'zod';

export const MembershipSchema = z.object({
  id: z.uuid(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }).nullable().optional(),
  archived: z.boolean(),

  organization_id: z.uuid(),
  user_id: z.uuid().nullable().optional(),
  role: z.string(),

  invited_by_id: z.uuid().nullable().optional(),
  invited_email: z.email().nullable().optional(),
  invitation_id: z.string().nullable().optional(),
  invitation_expires_at: z.iso.datetime({ offset: true }).nullable().optional(),

  additional_data: z.record(z.string(), z.unknown()),
});

export type MembershipResponse = z.infer<typeof MembershipSchema>;

export const MembershipRoleUpdateSchema = z.object({
  role: z.string().min(1),
});

export type UpdateMembershipRoleRequest = z.infer<
  typeof MembershipRoleUpdateSchema
>;
