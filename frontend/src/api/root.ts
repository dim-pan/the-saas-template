import { z } from 'zod';

import { apiGet } from '@/api/client';

export const rootResponseSchema = z.string();

export type RootResponse = z.infer<typeof rootResponseSchema>;

export async function getRoot(): Promise<RootResponse> {
  return apiGet('/', {}, rootResponseSchema);
}
