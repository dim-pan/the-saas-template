import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { initializeSegment } from './utils/segment';
import { createRouter, RouterProvider } from '@tanstack/react-router';
import { ROOT_ROUTE, ROUTES } from './routes/router';
import * as Sentry from '@sentry/react';
import { RecoilRoot } from 'recoil';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/components/auth/AuthProvider';

// Segment setup
const SEGMENT_WRITE_KEY = import.meta.env.VITE_SEGMENT_WRITE_KEY as
  | string
  | undefined;

if (!SEGMENT_WRITE_KEY) {
  console.warn('Segment key not set, analytics will not be initialized.');
} else {
  void initializeSegment(SEGMENT_WRITE_KEY);
}

// Tanstack Router setup
const routeTree = ROOT_ROUTE.addChildren(ROUTES);
const router = createRouter({ routeTree });

// TanStack Query setup
const queryClient = new QueryClient();

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

// Sentry setup
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN as string | undefined;
const SENTRY_ENV = import.meta.env.VITE_ENV as string | undefined;

const isSentryEnabled = SENTRY_DSN !== undefined;

if (isSentryEnabled && !SENTRY_DSN) {
  throw new Error('Sentry DSN is not set (VITE_SENTRY_DSN)');
}

Sentry.init({
  enabled: isSentryEnabled,
  dsn: SENTRY_DSN,
  environment: SENTRY_ENV,
  sendDefaultPii: true,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
    Sentry.tanstackRouterBrowserTracingIntegration(router),
  ],
  enableLogs: true,
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});

// ReactDOM setup
const HTMLRoot = document.getElementById('root');
if (!HTMLRoot) {
  throw new Error('Root element not found');
}

const root = createRoot(HTMLRoot, {
  onUncaughtError: Sentry.reactErrorHandler((error, errorInfo) => {
    console.warn('Uncaught error', error, errorInfo.componentStack);
  }),
  onCaughtError: Sentry.reactErrorHandler(),
  onRecoverableError: Sentry.reactErrorHandler(),
});

root.render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RecoilRoot>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </RecoilRoot>
    </QueryClientProvider>
  </StrictMode>,
);
