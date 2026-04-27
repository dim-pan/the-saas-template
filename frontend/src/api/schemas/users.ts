import { z } from 'zod';

export const UserSchema = z.object({
  id: z.uuid(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }).nullable().optional(),
  archived: z.boolean(),

  username: z.string().nullable().optional(),
  full_name: z.string().nullable().optional(),
  avatar_url: z.url().nullable().optional(),
  email: z.email(),
  additional_data: z.record(z.string(), z.unknown()),
});

export type UserResponse = z.infer<typeof UserSchema>;

export const UserUpdateSchema = z.object({
  username: z.string().nullable().optional(),
  full_name: z.string().nullable().optional(),
  avatar_url: z.url().nullable().optional(),
});

export type UpdateUserRequest = z.infer<typeof UserUpdateSchema>;
