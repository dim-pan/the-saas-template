import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/components/auth/AuthProvider';
import { listOrganizations } from '@/api/organizations';
import type { OrganizationResponse } from '@/api/schemas/organizations';

export function useOrganization() {
  const auth = useAuth();

  const organizationsQuery = useQuery<OrganizationResponse[]>({
    queryKey: ['organizations'],
    enabled: auth.isLoading === false && auth.user !== null,
    queryFn: async () => listOrganizations(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });

  const organization = useMemo(() => {
    const organizations = organizationsQuery.data
      ? organizationsQuery.data
      : [];

    if (organizations.length === 0) {
      return null;
    }

    // Return the first organization for now
    // Since users can't have multiple organizations yet.
    return organizations[0];
  }, [organizationsQuery.data]);

  return { organization, organizationsQuery };
}
