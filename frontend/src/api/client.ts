import { z } from 'zod';
import { supabase } from '@/supabase/client';

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

function getBackendUrl() {
  let backendUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;
  if (!backendUrl) {
    throw new Error('Backend URL is not set (VITE_BACKEND_URL)');
  }
  // Avoid mixed content: if the app is on HTTPS, force HTTPS for the API too.
  if (
    typeof window !== 'undefined' &&
    window.location.protocol === 'https:' &&
    backendUrl.startsWith('http://')
  ) {
    backendUrl = backendUrl.replace(/^http:\/\//i, 'https://');
  }
  return backendUrl;
}

async function getAccessToken() {
  const sessionResult = await supabase.auth.getSession();
  return sessionResult.data.session?.access_token ?? null;
}

async function parseJsonSafely(res: Response): Promise<unknown> {
  // Some endpoints might return empty bodies (204) or non-JSON error pages.
  const text = await res.text();
  if (text.trim().length === 0) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  auth?: boolean;
}

/**
 * Shared request helper that handles auth headers, JSON vs FormData bodies,
 * error parsing, and response validation in one place. The apiGet/apiPost/etc.
 * helpers are thin wrappers around this so the behavior stays consistent.
 */
export async function apiRequest<TResponse>(
  path: string,
  options: ApiRequestOptions,
  responseSchema: z.ZodType<TResponse>,
): Promise<TResponse> {
  const backendUrl = getBackendUrl();
  const url = new URL(path, backendUrl);
  const headers = new Headers(options.headers);
  const isFormData = options.body instanceof FormData;
  if (
    !headers.has('Content-Type') &&
    options.body !== undefined &&
    !isFormData
  ) {
    headers.set('Content-Type', 'application/json');
  }

  if (options.auth !== false) {
    const accessToken = await getAccessToken();
    if (!accessToken) {
      throw new ApiError('Missing Supabase session', 401, null);
    }
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  let requestBody: BodyInit | null | undefined;
  if (options.body === undefined) {
    requestBody = undefined;
  } else if (isFormData) {
    requestBody = options.body as FormData;
  } else {
    requestBody = JSON.stringify(options.body);
  }

  const res = await fetch(url, {
    method: options.method,
    headers,
    body: requestBody,
  });

  const parsedBody = await parseJsonSafely(res);
  if (!res.ok) {
    throw new ApiError('Request failed', res.status, parsedBody);
  }

  return responseSchema.parse(parsedBody);
}

export async function apiGet<TResponse>(
  path: string,
  options: Omit<ApiRequestOptions, 'method' | 'body'>,
  responseSchema: z.ZodType<TResponse>,
): Promise<TResponse> {
  return apiRequest(path, { ...options, method: 'GET' }, responseSchema);
}

export async function apiPatch<TResponse>(
  path: string,
  options: Omit<ApiRequestOptions, 'method'>,
  responseSchema: z.ZodType<TResponse>,
): Promise<TResponse> {
  return apiRequest(path, { ...options, method: 'PATCH' }, responseSchema);
}

export async function apiDelete<TResponse>(
  path: string,
  options: Omit<ApiRequestOptions, 'method' | 'body'>,
  responseSchema: z.ZodType<TResponse>,
): Promise<TResponse> {
  return apiRequest(path, { ...options, method: 'DELETE' }, responseSchema);
}

export async function apiPost<TResponse>(
  path: string,
  options: Omit<ApiRequestOptions, 'method'>,
  responseSchema: z.ZodType<TResponse>,
): Promise<TResponse> {
  return apiRequest(path, { ...options, method: 'POST' }, responseSchema);
}
