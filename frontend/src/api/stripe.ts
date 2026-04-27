import { z } from 'zod';

import { apiGet, apiPost } from '@/api/client';
import { OrganizationSchema } from '@/api/schemas/organizations';
import {
  CreateStripeCheckoutSessionRequestSchema,
  CreateStripeBillingPortalSessionRequestSchema,
  CreateStripeBillingPortalSessionResponseSchema,
  CreateStripeCustomerRequestSchema,
  StripeCatalogItemSchema,
  StripeCheckoutSessionSchema,
} from '@/api/schemas/stripe';
import type {
  CreateStripeCheckoutSessionRequest,
  CreateStripeBillingPortalSessionRequest,
  CreateStripeBillingPortalSessionResponse,
  CreateStripeCustomerRequest,
  StripeCatalogItemResponse,
  StripeCheckoutSessionResponse,
} from '@/api/schemas/stripe';

const stripeCatalogListSchema = z.array(StripeCatalogItemSchema);
const uuidSchema = z.uuid();

export async function listStripeCatalogItems(
  billingType?: 'subscription' | 'one_off',
): Promise<StripeCatalogItemResponse[]> {
  const params = new URLSearchParams();
  if (billingType) {
    params.set('billing_type', billingType);
  }

  const query = params.toString();
  const path =
    query.length > 0
      ? `/api/v1/stripe/catalog?${query}`
      : '/api/v1/stripe/catalog';

  return apiGet(path, { auth: false }, stripeCatalogListSchema);
}

export async function createStripeCustomer(
  organizationId: string,
  payload: CreateStripeCustomerRequest = {},
) {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedPayload = CreateStripeCustomerRequestSchema.parse(payload);

  return apiPost(
    `/api/v1/org/${parsedOrganizationId}/stripe/customer`,
    { body: parsedPayload },
    OrganizationSchema,
  );
}

export async function createStripeCheckoutSession(
  organizationId: string,
  payload: CreateStripeCheckoutSessionRequest,
): Promise<StripeCheckoutSessionResponse> {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedPayload = CreateStripeCheckoutSessionRequestSchema.parse(payload);

  return apiPost(
    `/api/v1/org/${parsedOrganizationId}/stripe/checkout-session`,
    { body: parsedPayload },
    StripeCheckoutSessionSchema,
  );
}

export async function createStripeBillingPortalSession(
  organizationId: string,
  payload: CreateStripeBillingPortalSessionRequest,
): Promise<CreateStripeBillingPortalSessionResponse> {
  const parsedOrganizationId = uuidSchema.parse(organizationId);
  const parsedPayload =
    CreateStripeBillingPortalSessionRequestSchema.parse(payload);

  return apiPost(
    `/api/v1/org/${parsedOrganizationId}/stripe/billing-portal-session`,
    { body: parsedPayload },
    CreateStripeBillingPortalSessionResponseSchema,
  );
}
