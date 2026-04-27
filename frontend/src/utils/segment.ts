import { AnalyticsBrowser, Analytics } from '@segment/analytics-next';

let analytics: Analytics | null = null;

export async function initializeSegment(writeKey: string) {
  // If analytics is not initialized, initialize it
  if (!analytics) {
    const [instance] = await AnalyticsBrowser.load(
      { writeKey },
      { disableClientPersistence: false },
    );
    analytics = instance;
  }

  console.debug('[Segment] Analytics initialized');
  return analytics;
}

export const track = (event: string, props?: Record<string, unknown>) => {
  if (!analytics) return;
  console.debug('[Segment] Tracking event', event, props);
  void analytics.track(event, props);
};

export const identify = (id: string, traits?: Record<string, unknown>) => {
  if (!analytics) return;
  console.debug('[Segment] Identifying user', id, traits);
  void analytics.identify(id, traits);
};
