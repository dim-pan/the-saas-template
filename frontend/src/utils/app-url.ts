/**
 * Canonical base URL for the frontend (used for auth redirects, etc.).
 * Set VITE_APP_URL in production so email links redirect to the deployed app, not localhost.
 */
export function getAppOrigin(): string {
  const fromEnv = import.meta.env.VITE_APP_URL as string | undefined;
  if (fromEnv?.trim()) {
    return fromEnv.replace(/\/$/, '');
  }
  return window.location.origin;
}
