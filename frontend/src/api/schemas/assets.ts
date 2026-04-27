import { z } from 'zod';

export const AssetUploadRequestSchema = z.object({
  filename: z.string(),
  size_bytes: z.number(),
  mime_type: z.string(),
});

export type AssetUploadRequest = z.infer<typeof AssetUploadRequestSchema>;

export const AssetUploadResponseSchema = z.object({
  upload_url: z.url(),
  asset_id: z.uuid(),
  provider: z.enum(['r2', 'image', 'stream']),
});

export type AssetUploadResponse = z.infer<typeof AssetUploadResponseSchema>;

export const CompleteUploadRequestSchema = z.object({
  asset_id: z.uuid(),
  mime_type: z.string(),
});

export type CompleteUploadRequest = z.infer<typeof CompleteUploadRequestSchema>;

export const CompleteUploadResponseSchema = z.object({
  asset_id: z.uuid(),
});

export type CompleteUploadResponse = z.infer<
  typeof CompleteUploadResponseSchema
>;

export const AssetSchema = z.object({
  id: z.uuid(),
  asset_id: z.uuid(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }).nullable().optional(),
  deleted_at: z.iso.datetime({ offset: true }).nullable().optional(),
  organization_id: z.uuid(),
  user_id: z.uuid(),
  filename: z.string(),
  storage_key: z.string(),
  thumbnail_url: z.string().nullable().optional(),
  mime_type: z.string(),
  status: z.enum(['pending', 'uploaded', 'failed']),
  size_bytes: z.number().nullable().optional(),
  provider: z.enum(['r2', 'image', 'stream']),
});

export const ListAssetsResponseSchema = z.array(AssetSchema);

export type ListAssetsResponse = z.infer<typeof ListAssetsResponseSchema>;

export const GetAssetResponseSchema = z.object({
  url: z.string(),
  asset: AssetSchema,
});

export type GetAssetResponse = z.infer<typeof GetAssetResponseSchema>;
