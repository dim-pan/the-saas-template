import { useQuery } from '@tanstack/react-query';
import { listJobs } from '@/api/jobs';
import type { Job } from '@/api/schemas/jobs';
import { useOrganization } from '@/hooks/useOrganization';

export const JOBS_QUERY_KEY = 'jobs';

const POLL_INTERVAL_MS = 4000;

function hasActiveJobs(jobs: Job[]): boolean {
  return jobs.some((j) => j.status === 'queued' || j.status === 'processing');
}

export function useJobs() {
  const { organization } = useOrganization();

  const jobsQuery = useQuery({
    queryKey: [JOBS_QUERY_KEY, organization?.id],
    queryFn: async () => {
      if (!organization?.id) {
        throw new Error('Organization ID is required');
      }
      return listJobs(organization.id);
    },
    enabled: !!organization?.id,
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    refetchOnMount: true,
    refetchInterval: (query) =>
      hasActiveJobs(query.state.data ?? []) ? POLL_INTERVAL_MS : false,
  });

  const jobs = jobsQuery.data ?? [];

  return {
    jobs,
    jobsQuery,
  };
}
