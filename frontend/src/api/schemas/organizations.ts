import { z } from 'zod';

export const OrganizationSchema = z.object({
  id: z.uuid(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }).nullable().optional(),
  archived: z.boolean(),
  billing_email: z.string().nullable().optional(),
  stripe_customer_id: z.string().nullable().optional(),
  additional_data: z.record(z.string(), z.unknown()),

  billing_plan_key: z.string().nullable().optional(),
  billing_status: z.string().nullable().optional(),
  billing_is_paid: z.boolean(),
  billing_cancel_at_period_end: z.boolean(),
  billing_current_period_start: z.iso
    .datetime({ offset: true })
    .nullable()
    .optional(),
  billing_current_period_end: z.iso
    .datetime({ offset: true })
    .nullable()
    .optional(),
  billing_updated_at: z.iso.datetime({ offset: true }).nullable().optional(),

  name: z.string(),
});

export type OrganizationResponse = z.infer<typeof OrganizationSchema>;

export const OrganizationUpdateRequestSchema = z.object({
  name: z.string().min(1).optional(),
});

export type OrganizationUpdateRequest = z.infer<
  typeof OrganizationUpdateRequestSchema
>;
