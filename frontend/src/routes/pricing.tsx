import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  createStripeCheckoutSession,
  createStripeBillingPortalSession,
  createStripeCustomer,
  listStripeCatalogItems,
} from '@/api/stripe';
import { listOrganizations } from '@/api/organizations';

interface PricingTier {
  key: string;
  name: string;
  price: string;
  description: string;
  features: string[];
  isFeatured?: boolean;
}

type BillingPeriod = 'monthly' | 'yearly';

export function Pricing() {
  const organizationsQuery = useQuery({
    queryKey: ['organizations'],
    queryFn: async () => {
      return listOrganizations();
    },
  });

  const stripeCatalogQuery = useQuery({
    queryKey: ['stripe_catalog', 'subscription'],
    queryFn: async () => {
      return listStripeCatalogItems('subscription');
    },
  });

  const stripeOneOffCatalogQuery = useQuery({
    queryKey: ['stripe_catalog', 'one_off'],
    queryFn: async () => {
      return listStripeCatalogItems('one_off');
    },
  });

  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>('monthly');

  const activeOrganizationId = useMemo(() => {
    const firstOrgId = organizationsQuery.data?.[0]?.id ?? null;
    return firstOrgId;
  }, [organizationsQuery.data]);

  const activeOrganization = useMemo(() => {
    const organizations = organizationsQuery.data ?? [];
    const org = organizations.find(
      (candidate) => candidate.id === activeOrganizationId,
    );
    return org ?? null;
  }, [activeOrganizationId, organizationsQuery.data]);

  const [stripeCustomerStatus, setStripeCustomerStatus] = useState<
    string | null
  >(null);

  const [billingPortalStatus, setBillingPortalStatus] = useState<string | null>(
    null,
  );

  const [checkoutStatus, setCheckoutStatus] = useState<string | null>(null);
  const [checkoutPendingCatalogKey, setCheckoutPendingCatalogKey] = useState<
    string | null
  >(null);

  const createStripeCustomerMutation = useMutation({
    mutationFn: async () => {
      if (!activeOrganizationId) {
        throw new Error('Missing organization id');
      }
      return createStripeCustomer(activeOrganizationId);
    },
    onSuccess: (org) => {
      const customerId = org.stripe_customer_id ?? null;
      if (customerId) {
        setStripeCustomerStatus(`Stripe customer created: ${customerId}`);
        return;
      }
      setStripeCustomerStatus(
        'Stripe customer already exists (or was not returned).',
      );
    },
    onError: () => {
      setStripeCustomerStatus('Failed to create Stripe customer.');
    },
  });

  const createCheckoutSessionMutation = useMutation({
    mutationFn: async (catalogKey: string) => {
      if (!activeOrganizationId) {
        throw new Error('Missing organization id');
      }
      const successUrl = `${window.location.origin}/upgrade?checkout=success`;
      const cancelUrl = window.location.href;

      return createStripeCheckoutSession(activeOrganizationId, {
        catalog_key: catalogKey,
        success_url: successUrl,
        cancel_url: cancelUrl,
      });
    },
    onMutate: (catalogKey) => {
      setCheckoutStatus(null);
      setCheckoutPendingCatalogKey(catalogKey);
    },
    onSuccess: (session) => {
      window.location.href = session.url;
    },
    onError: () => {
      setCheckoutStatus('Failed to start checkout.');
    },
    onSettled: () => {
      setCheckoutPendingCatalogKey(null);
    },
  });

  const createBillingPortalSessionMutation = useMutation({
    mutationFn: async () => {
      if (!activeOrganizationId) {
        throw new Error('Missing organization id');
      }
      return createStripeBillingPortalSession(activeOrganizationId, {
        return_url: window.location.href,
      });
    },
    onMutate: () => {
      setBillingPortalStatus(null);
    },
    onSuccess: (session) => {
      window.location.href = session.url;
    },
    onError: () => {
      setBillingPortalStatus('Failed to open billing portal.');
    },
  });

  const formattedBillingPeriodStart = useMemo(() => {
    const raw = activeOrganization?.billing_current_period_start ?? null;
    if (!raw) return null;
    const dt = new Date(raw);
    if (Number.isNaN(dt.getTime())) return raw;
    return dt.toLocaleString();
  }, [activeOrganization?.billing_current_period_start]);

  const formattedBillingPeriodEnd = useMemo(() => {
    const raw = activeOrganization?.billing_current_period_end ?? null;
    if (!raw) return null;
    const dt = new Date(raw);
    if (Number.isNaN(dt.getTime())) return raw;
    return dt.toLocaleString();
  }, [activeOrganization?.billing_current_period_end]);

  const formattedBillingUpdatedAt = useMemo(() => {
    const raw = activeOrganization?.billing_updated_at ?? null;
    if (!raw) return null;
    const dt = new Date(raw);
    if (Number.isNaN(dt.getTime())) return raw;
    return dt.toLocaleString();
  }, [activeOrganization?.billing_updated_at]);

  const createStripeCustomerButtonLabel = useMemo(() => {
    if (createStripeCustomerMutation.isPending) {
      return 'Creating…';
    }
    if (activeOrganization?.stripe_customer_id) {
      return 'Stripe customer exists';
    }
    return 'Create Stripe customer';
  }, [
    activeOrganization?.stripe_customer_id,
    createStripeCustomerMutation.isPending,
  ]);

  const selectedStripeItems = useMemo(() => {
    const items = stripeCatalogQuery.data ?? [];
    const interval = billingPeriod === 'monthly' ? 'month' : 'year';

    return items
      .filter((item) => {
        const itemInterval = item.billing_interval ?? null;
        const itemIntervalCount = item.billing_interval_count ?? null;
        if (itemInterval !== interval) return false;
        if (itemIntervalCount !== null && itemIntervalCount !== 1) return false;
        return true;
      })
      .sort((a, b) => {
        const aRank = a.rank ?? 0;
        const bRank = b.rank ?? 0;
        return aRank - bRank;
      })
      .slice(0, 3);
  }, [billingPeriod, stripeCatalogQuery.data]);

  const pricingTiers = useMemo((): PricingTier[] => {
    if (stripeCatalogQuery.isLoading || stripeCatalogQuery.isError) return [];
    if (selectedStripeItems.length === 0) return [];

    return selectedStripeItems.map((item) => {
      const displayPrice =
        item.display_price_discounted ?? item.display_price ?? '—';

      return {
        key: item.key,
        name: item.name ?? item.key,
        price: displayPrice,
        description: item.description ?? '',
        features: item.feature_set,
        isFeatured: item.rank === 2,
      };
    });
  }, [
    selectedStripeItems,
    stripeCatalogQuery.isError,
    stripeCatalogQuery.isLoading,
  ]);

  return (
    <div className="p-6">
      <div className="mx-auto w-full max-w-6xl">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold text-foreground">Pricing</h1>
          <p className="text-sm text-muted-foreground">
            Choose the plan that fits your needs. (Dummy content for now.)
          </p>
        </div>

        <div className="mt-4">
          {stripeCatalogQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Loading pricing…</p>
          )}
          {stripeCatalogQuery.isError && (
            <p className="text-sm text-destructive">Failed to load pricing.</p>
          )}
        </div>

        <div className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Billing</CardTitle>
              <CardDescription>
                Create and attach a Stripe customer to your current
                organization.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex flex-col gap-3 sm:min-w-0">
                  <p className="text-sm text-muted-foreground break-all">
                    Org: {activeOrganizationId ?? 'No organization found'}
                  </p>

                  <p className="text-sm text-muted-foreground break-all">
                    Stripe customer:{' '}
                    {activeOrganization?.stripe_customer_id ?? '—'}
                  </p>

                  {activeOrganization && (
                    <div className="mt-1 flex flex-col gap-2 text-sm text-muted-foreground">
                      <p className="break-all">
                        Plan: {activeOrganization.billing_plan_key ?? '—'}
                      </p>
                      <p className="break-all">
                        Status: {activeOrganization.billing_status ?? '—'}
                      </p>
                      <p>
                        Paid:{' '}
                        {activeOrganization.billing_is_paid ? 'Yes' : 'No'}
                      </p>
                      <p>
                        Cancel at period end:{' '}
                        {activeOrganization.billing_cancel_at_period_end
                          ? 'Yes'
                          : 'No'}
                      </p>
                      <p className="break-all">
                        Period start: {formattedBillingPeriodStart ?? '—'}
                      </p>
                      <p className="break-all">
                        Period end: {formattedBillingPeriodEnd ?? '—'}
                      </p>
                      <p className="break-all">
                        Updated at: {formattedBillingUpdatedAt ?? '—'}
                      </p>
                    </div>
                  )}
                </div>

                <div className="flex w-full flex-col gap-3 sm:w-64 sm:shrink-0">
                  <Button
                    isDisabled={
                      organizationsQuery.isLoading ||
                      organizationsQuery.isError ||
                      !activeOrganization?.stripe_customer_id ||
                      createBillingPortalSessionMutation.isPending
                    }
                    onClick={() => {
                      setBillingPortalStatus(null);
                      createBillingPortalSessionMutation.mutate();
                    }}
                  >
                    {createBillingPortalSessionMutation.isPending
                      ? 'Opening…'
                      : 'Manage billing'}
                  </Button>

                  {billingPortalStatus && (
                    <p className="text-sm text-muted-foreground">
                      {billingPortalStatus}
                    </p>
                  )}

                  <Button
                    isDisabled={
                      organizationsQuery.isLoading ||
                      organizationsQuery.isError ||
                      !activeOrganizationId ||
                      !!activeOrganization?.stripe_customer_id ||
                      createStripeCustomerMutation.isPending
                    }
                    onClick={() => {
                      setStripeCustomerStatus(null);
                      createStripeCustomerMutation.mutate();
                    }}
                  >
                    {createStripeCustomerButtonLabel}
                  </Button>

                  {stripeCustomerStatus && (
                    <p className="text-sm text-muted-foreground">
                      {stripeCustomerStatus}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 flex items-center gap-2">
          <Button
            variant={billingPeriod === 'monthly' ? 'secondary' : 'outline'}
            onClick={() => {
              setBillingPeriod('monthly');
            }}
          >
            Monthly
          </Button>
          <Button
            variant={billingPeriod === 'yearly' ? 'secondary' : 'outline'}
            onClick={() => {
              setBillingPeriod('yearly');
            }}
          >
            Yearly
          </Button>
        </div>

        {checkoutStatus && (
          <p className="mt-3 text-sm text-destructive">{checkoutStatus}</p>
        )}

        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {stripeCatalogQuery.isLoading && (
            <>
              {Array.from({ length: 3 }).map((_, idx) => {
                return (
                  <Card
                    key={`pricing-skeleton-${idx}`}
                    className="animate-pulse"
                  >
                    <CardHeader>
                      <div className="flex items-baseline justify-between gap-3">
                        <div className="h-5 w-1/3 rounded bg-muted" />
                        <div className="h-7 w-1/4 rounded bg-muted" />
                      </div>
                      <div className="mt-2 h-4 w-5/6 rounded bg-muted" />
                    </CardHeader>
                    <CardContent className="flex flex-col gap-5">
                      <div className="flex flex-col gap-2">
                        <div className="h-4 w-5/6 rounded bg-muted" />
                        <div className="h-4 w-4/6 rounded bg-muted" />
                        <div className="h-4 w-3/6 rounded bg-muted" />
                        <div className="h-4 w-4/6 rounded bg-muted" />
                      </div>
                      <div className="h-10 w-full rounded bg-muted" />
                    </CardContent>
                  </Card>
                );
              })}
            </>
          )}

          {!stripeCatalogQuery.isLoading &&
            pricingTiers.map((tier) => {
              const isCheckoutPendingForTier =
                checkoutPendingCatalogKey === tier.key;

              return (
                <Card
                  key={tier.key}
                  className={
                    tier.isFeatured ? 'border-primary/40 shadow-sm' : undefined
                  }
                >
                  <CardHeader>
                    <CardTitle className="flex items-baseline justify-between gap-3">
                      <span>{tier.name}</span>
                      <span className="text-2xl font-semibold text-foreground">
                        {tier.price}
                      </span>
                    </CardTitle>
                    <CardDescription>{tier.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-5">
                    <ul className="flex flex-col gap-2">
                      {tier.features.map((feature) => {
                        return (
                          <li
                            key={feature}
                            className="flex items-start gap-2 text-sm text-foreground"
                          >
                            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/80" />
                            <span className="text-muted-foreground">
                              {feature}
                            </span>
                          </li>
                        );
                      })}
                    </ul>

                    <Button
                      className="w-full"
                      isDisabled={
                        stripeCatalogQuery.isLoading ||
                        stripeCatalogQuery.isError ||
                        organizationsQuery.isLoading ||
                        organizationsQuery.isError ||
                        !activeOrganizationId ||
                        checkoutPendingCatalogKey === tier.key
                      }
                      onClick={() => {
                        if (
                          checkoutPendingCatalogKey !== null &&
                          checkoutPendingCatalogKey !== tier.key
                        ) {
                          setCheckoutStatus('Checkout is already in progress.');
                          return;
                        }
                        void createCheckoutSessionMutation.mutate(tier.key);
                      }}
                    >
                      {isCheckoutPendingForTier
                        ? 'Redirecting…'
                        : 'Get Started'}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
        </div>

        {!stripeCatalogQuery.isLoading &&
          !stripeCatalogQuery.isError &&
          pricingTiers.length === 0 && (
            <p className="mt-4 text-sm text-muted-foreground">
              No pricing is available yet.
            </p>
          )}

        <div className="mt-8">
          {stripeOneOffCatalogQuery.isLoading && (
            <Card className="animate-pulse">
              <CardHeader>
                <div className="h-5 w-1/3 rounded bg-muted" />
                <div className="mt-2 h-4 w-5/6 rounded bg-muted" />
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div className="h-10 w-full rounded bg-muted" />
              </CardContent>
            </Card>
          )}

          {stripeOneOffCatalogQuery.isError && (
            <p className="text-sm text-destructive">
              Failed to load one-time purchase.
            </p>
          )}

          {!stripeOneOffCatalogQuery.isLoading &&
            !stripeOneOffCatalogQuery.isError &&
            stripeOneOffCatalogQuery.data &&
            stripeOneOffCatalogQuery.data.length > 0 &&
            (() => {
              const oneOffItem = stripeOneOffCatalogQuery.data[0];
              const displayPrice =
                oneOffItem.display_price_discounted ??
                oneOffItem.display_price ??
                '—';
              const isCheckoutPendingForOneOff =
                checkoutPendingCatalogKey === oneOffItem.key;

              return (
                <Card>
                  <CardHeader>
                    <CardTitle>
                      {oneOffItem.name ?? 'One-time purchase'}
                    </CardTitle>
                    <CardDescription>
                      {oneOffItem.description ?? 'One-off payment'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <p className="text-sm text-muted-foreground">
                      Price: {displayPrice}
                    </p>
                    <Button
                      className="w-full"
                      isDisabled={
                        organizationsQuery.isLoading ||
                        organizationsQuery.isError ||
                        !activeOrganizationId ||
                        checkoutPendingCatalogKey === oneOffItem.key
                      }
                      onClick={() => {
                        if (
                          checkoutPendingCatalogKey !== null &&
                          checkoutPendingCatalogKey !== oneOffItem.key
                        ) {
                          setCheckoutStatus('Checkout is already in progress.');
                          return;
                        }
                        void createCheckoutSessionMutation.mutate(
                          oneOffItem.key,
                        );
                      }}
                    >
                      {isCheckoutPendingForOneOff
                        ? 'Redirecting…'
                        : 'Buy one-time'}
                    </Button>
                  </CardContent>
                </Card>
              );
            })()}
        </div>
      </div>
    </div>
  );
}
