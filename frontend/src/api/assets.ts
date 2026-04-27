import { z } from 'zod';

import { apiDelete, apiGet, apiPost } from '@/api/client';
import {
  AssetUploadResponseSchema,
  CompleteUploadResponseSchema,
  GetAssetResponseSchema,
  ListAssetsResponseSchema,
  type AssetUploadRequest,
  type CompleteUploadRequest,
  type GetAssetResponse,
} from '@/api/schemas/assets';

export async function uploadAsset(
  payload: AssetUploadRequest,
  organizationId: string,
) {
  const path = `/api/v1/org/${encodeURIComponent(organizationId)}/assets/uploads`;
  return apiPost(path, { body: payload }, AssetUploadResponseSchema);
}

export async function completeUpload(
  organizationId: string,
  payload: CompleteUploadRequest,
) {
  const path = `/api/v1/org/${encodeURIComponent(organizationId)}/assets/uploads/${encodeURIComponent(payload.asset_id)}/complete`;
  return apiPost(path, { body: payload }, CompleteUploadResponseSchema);
}

export async function listAssets(organizationId: string) {
  const path = `/api/v1/org/${encodeURIComponent(organizationId)}/assets`;
  return apiGet(path, {}, ListAssetsResponseSchema);
}

export async function getAsset(
  assetId: string,
  organizationId: string,
): Promise<GetAssetResponse> {
  const path = `/api/v1/org/${encodeURIComponent(organizationId)}/assets/${encodeURIComponent(assetId)}`;
  return apiGet(path, {}, GetAssetResponseSchema);
}

export async function deleteAsset(assetId: string, organizationId: string) {
  const path = `/api/v1/org/${encodeURIComponent(organizationId)}/assets/${encodeURIComponent(assetId)}`;
  return apiDelete(path, {}, z.null());
}
