import { z } from 'zod';

export const CreateStripeCustomerRequestSchema = z.object({
  billing_email: z.email().nullable().optional(),
});

export type CreateStripeCustomerRequest = z.infer<
  typeof CreateStripeCustomerRequestSchema
>;

export const CreateStripeCheckoutSessionRequestSchema = z.object({
  catalog_key: z.string().min(1),
  success_url: z.string().min(1),
  cancel_url: z.string().min(1),
});

export type CreateStripeCheckoutSessionRequest = z.infer<
  typeof CreateStripeCheckoutSessionRequestSchema
>;

export const StripeCheckoutSessionSchema = z.object({
  id: z.string().min(1),
  url: z.string().min(1),
});

export type StripeCheckoutSessionResponse = z.infer<
  typeof StripeCheckoutSessionSchema
>;

export const CreateStripeBillingPortalSessionRequestSchema = z.object({
  return_url: z.url(),
  flow_data: z.record(z.string(), z.unknown()).nullable().optional(),
});

export type CreateStripeBillingPortalSessionRequest = z.infer<
  typeof CreateStripeBillingPortalSessionRequestSchema
>;

export const CreateStripeBillingPortalSessionResponseSchema = z.object({
  url: z.url(),
});

export type CreateStripeBillingPortalSessionResponse = z.infer<
  typeof CreateStripeBillingPortalSessionResponseSchema
>;

export const StripeCatalogItemSchema = z.object({
  id: z.uuid(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }).nullable().optional(),
  archived: z.boolean(),

  key: z.string(),
  name: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  feature_set: z.array(z.string()),

  billing_type: z.enum(['subscription', 'one_off']),

  stripe_product_id: z.string(),
  stripe_price_id: z.string(),

  plan_family: z.string().nullable().optional(),
  rank: z.number().int().nullable().optional(),
  billing_interval: z.string().nullable().optional(),
  billing_interval_count: z.number().int().nullable().optional(),

  default_stripe_coupon_id: z.string().nullable().optional(),
  override_stripe_coupon_id: z.string().nullable().optional(),

  additional_data: z.record(z.string(), z.unknown()),

  display_price: z.string().nullable().optional(),
  display_price_discounted: z.string().nullable().optional(),
});

export type StripeCatalogItemResponse = z.infer<typeof StripeCatalogItemSchema>;
