import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useOrganization } from '@/hooks/useOrganization';
import { deleteAsset, getAsset, listAssets } from '@/api/assets';
import { uploadFile } from '@/api/cloudflare';
import { useCallback } from 'react';

export const ASSETS_QUERY_KEY = 'assets';

export function useAssets() {
  const { organization } = useOrganization();
  const queryClient = useQueryClient();

  const assetsQuery = useQuery({
    queryKey: [ASSETS_QUERY_KEY, organization?.id],
    queryFn: async () => {
      if (!organization?.id) {
        throw new Error('Organization ID is required');
      }
      return listAssets(organization.id);
    },
    enabled: !!organization?.id,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });

  const uploadMutation = useMutation({
    mutationFn: async ({
      file,
      organizationId,
    }: {
      file: File;
      organizationId: string;
    }) => {
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }
      return uploadFile(file, organizationId);
    },
    onSuccess: async (_, variables) => {
      const organizationId = variables.organizationId;
      if (!organizationId) {
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: [ASSETS_QUERY_KEY, organizationId],
      });
      await queryClient.refetchQueries({
        queryKey: [ASSETS_QUERY_KEY, organizationId],
      });
    },
  });

  const deleteMutation = useMutation<null, Error, string>({
    mutationFn: async (assetId: string) => {
      const organizationId = organization?.id;
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }
      return deleteAsset(assetId, organizationId);
    },
    onSuccess: async () => {
      const organizationId = organization?.id;
      if (!organizationId) {
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: [ASSETS_QUERY_KEY, organizationId],
      });
    },
  });

  const getAssetUrl = useCallback(
    async (assetId: string) => {
      const organizationId = organization?.id;
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }

      const response = await queryClient.fetchQuery({
        queryKey: ['asset-url', organizationId, assetId],
        queryFn: () => getAsset(assetId, organizationId),
        staleTime: 60 * 60 * 1000, // 1 hour
      });
      return response.url;
    },
    [organization?.id, queryClient],
  );

  const assets = assetsQuery.data ?? [];

  const deleteAssetAction = useCallback(
    async (assetId: string): Promise<null> => {
      return deleteMutation.mutateAsync(assetId);
    },
    [deleteMutation],
  );

  const uploadAsset = useCallback<(file: File) => Promise<void>>(
    async (file) => {
      const organizationId = organization?.id;
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }
      await uploadMutation.mutateAsync({ file, organizationId });
    },
    [organization?.id, uploadMutation],
  );

  return {
    assets,
    uploadAsset,
    deleteAsset: deleteAssetAction,
    getAssetUrl,
  };
}
