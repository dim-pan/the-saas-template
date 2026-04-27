import { completeUpload, uploadAsset } from './assets';

export async function uploadFile(file: File, organizationId: string) {
  const fileType = file.type;

  // 1. Get presigned URL
  console.info(`Fetching presigned URL from Cloudflare: ${file.name}`);
  const uploadAssetResponse = await uploadAsset(
    {
      filename: file.name,
      size_bytes: file.size,
      mime_type: fileType,
    },
    organizationId,
  );

  const uploadUrl = uploadAssetResponse.upload_url;
  const assetId = uploadAssetResponse.asset_id;
  const provider = uploadAssetResponse.provider;
  console.info(
    `Presigned URL fetched from Cloudflare: ${uploadUrl} for asset ${assetId}`,
  );

  if (!uploadUrl || !assetId) {
    console.error('FRONTEND->PRESIGN response invalid');
    throw new Error('FRONTEND->PRESIGN response invalid');
  }

  // 2. Upload file to presigned URL (Cloudflare) — method/body depend on provider
  let uploadInit: RequestInit;
  switch (provider) {
    case 'image': {
      // Direct Creator Upload: POST multipart/form-data, field "file"
      const form = new FormData();
      form.append('file', file);
      uploadInit = { method: 'POST', body: form };
      break;
    }
    case 'r2':
      uploadInit = { method: 'PUT', body: file };
      break;
    case 'stream': {
      // Stream direct upload: POST multipart/form-data, field "file"
      const form = new FormData();
      form.append('file', file);
      uploadInit = { method: 'POST', body: form };
      break;
    }
    default: {
      const _exhaust: never = provider;
      throw new Error(`Unknown Cloudflare provider: ${String(_exhaust)}`);
    }
  }

  console.info(
    `Uploading file to Cloudflare: ${file.name} for asset ${assetId}`,
  );
  await fetch(uploadUrl, uploadInit)
    .then(() => {
      console.info(
        `File uploaded to Cloudflare: ${file.name} for asset ${assetId}`,
      );
    })
    .catch((error) => {
      console.error(
        `Failed to upload file to Cloudflare: ${file.name} for asset ${assetId}`,
        error,
      );
      throw error;
    });

  // 3. Send the confirmation request (Backend)
  console.info(`Sending confirmation request to backend: ${file.name}`);
  await completeUpload(organizationId, {
    asset_id: assetId,
    mime_type: fileType,
  });

  console.info(`Confirmation request sent to backend: ${file.name}`);
}
