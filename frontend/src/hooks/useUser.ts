import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/components/auth/AuthProvider';
import { useOrganization } from '@/hooks/useOrganization';
import { getUser } from '@/api/users';
import type { UserResponse } from '@/api/schemas/users';

export const USER_QUERY_KEY = 'users';

export function useUser() {
  const auth = useAuth();
  const { organization } = useOrganization();

  const userId = auth.user?.id ?? null;
  const organizationId = organization?.id ?? null;

  const userQuery = useQuery<UserResponse>({
    queryKey: [USER_QUERY_KEY, organizationId, userId],
    queryFn: async () => {
      if (!organizationId || !userId) {
        throw new Error('Organization and user are required');
      }
      return getUser(organizationId, userId);
    },
    enabled:
      auth.isLoading === false &&
      auth.user !== null &&
      !!organizationId &&
      !!userId,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const user = userQuery.data ?? null;

  return { user, userQuery };
}
