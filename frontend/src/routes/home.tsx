import { createJob } from '@/api/jobs';
import type { Job } from '@/api/schemas/jobs';
import { JOBS_QUERY_KEY, useJobs } from '@/hooks/useJobs';
import { useQueryClient } from '@tanstack/react-query';
import { useMemo, useState, useEffect, type FormEvent } from 'react';
import { useOrganization } from '@/hooks/useOrganization';
import { useAssets } from '@/hooks/useAssets';
import { useUser } from '@/hooks/useUser';
import { TrashIcon } from 'lucide-react';

export function Home() {
  const queryClient = useQueryClient();
  const { jobs } = useJobs();
  const { user } = useUser();
  const { organization } = useOrganization();
  const { assets, getAssetUrl, deleteAsset, uploadAsset } = useAssets();
  const [uploadStatus, setUploadStatus] = useState('idle');

  const handleAssetClick = async (assetId: string) => {
    try {
      const assetUrl = await getAssetUrl(assetId);
      window.open(assetUrl, '_blank');
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      console.error('Failed to fetch asset URL', errorMessage);
    }
  };

  const handleDeleteAsset = async (assetId: string) => {
    try {
      await deleteAsset(assetId);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      console.error('Failed to delete asset', errorMessage);
    }
  };
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    if (!organization?.id) return;
    event.preventDefault();
    setUploadStatus('uploading');
    const formData = new FormData(event.currentTarget);
    const fileEntry = formData.get('file');

    if (!(fileEntry instanceof File)) {
      setUploadStatus('error');
      return;
    }

    try {
      await uploadAsset(fileEntry);
      setUploadStatus('idle');
    } catch {
      setUploadStatus('error');
    }
  };

  const invalidateJobs = () => {
    if (organization?.id) {
      void queryClient.invalidateQueries({
        queryKey: [JOBS_QUERY_KEY, organization.id],
      });
    }
  };

  const triggerJobA = () => {
    if (!organization?.id) return;
    void createJob(organization.id, {
      task: 'example_task_1',
      data: { name: 'Alice' },
    }).then(invalidateJobs);
  };
  const triggerJobB = () => {
    if (!organization?.id) return;
    void createJob(organization.id, {
      task: 'example_task_2',
      data: { name: 'Bob' },
    }).then(invalidateJobs);
  };
  const triggerJobC = () => {
    if (!organization?.id) return;
    void createJob(organization.id, {
      task: 'example_task_3',
      data: { name: 'Alex' },
    }).then(invalidateJobs);
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold text-foreground">Home section</h1>
      <p className="text-sm text-muted-foreground">
        You are authenticated if you can see this page.
      </p>

      {/* File upload */}
      <span>Upload status: {uploadStatus}</span>
      <form
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
      >
        <input
          type="file"
          name="file"
          className="border border-gray-300 p-2 rounded-md"
        />
        <button type="submit" className="bg-blue-500 text-white p-2 rounded-md">
          Upload
        </button>
      </form>
      <div className="flex gap-2">
        <button
          className="bg-blue-700 hover:bg-blue-800 cursor-pointer rounded px-4 py-2  text-white"
          onClick={() => {
            void triggerJobA();
          }}
        >
          Trigger job 1
        </button>
        <button
          className="bg-blue-700 hover:bg-blue-800 cursor-pointer rounded px-4 py-2  text-white"
          onClick={() => {
            void triggerJobB();
          }}
        >
          Trigger job 2
        </button>
        <button
          className="bg-blue-700 hover:bg-blue-800 cursor-pointer rounded px-4 py-2  text-white"
          onClick={() => {
            void triggerJobC();
          }}
        >
          Trigger job 3
        </button>
      </div>

      {/* Job list */}
      <div className="mt-8 flex flex-col gap-2">
        <h2 className="text-lg font-medium text-foreground">Jobs</h2>
        {jobs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No jobs yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {jobs.map((job) => (
              <li key={job.id}>
                <JobStatus job={job} />
              </li>
            ))}
          </ul>
        )}
      </div>
      <h4>Organization ID: {organization?.id}</h4>
      <h4>User ID: {user?.id}</h4>
      <div className="grid grid-cols-3 gap-4">
        {assets.map((asset) => {
          const hasThumbnail = asset.thumbnail_url !== null;
          if (hasThumbnail) {
            return (
              <div
                key={asset.id}
                className="relative bg-gray-100 rounded-2xl flex items-center justify-center w-42 h-42"
              >
                <button
                  type="button"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    void handleDeleteAsset(asset.asset_id);
                  }}
                  className="bg-red-200 cursor-pointer text-white p-2 rounded-md absolute top-2 right-2 z-10"
                >
                  <TrashIcon className="w-4 h-4 text-gray-500" />
                </button>
                <button
                  type="button"
                  className="w-42 h-42 bg-gray-100 rounded-2xl cursor-pointer flex items-center justify-center overflow-hidden p-4"
                  key={asset.id}
                  onClick={() => {
                    void handleAssetClick(asset.asset_id);
                  }}
                >
                  <img
                    className="w-full h-full object-fit rounded-2xl"
                    src={asset.thumbnail_url ?? ''}
                    alt={asset.filename}
                  />
                </button>
              </div>
            );
          }
        })}
      </div>
    </div>
  );
}

function expectedDurationSec(task: string): number {
  if (task === 'example_task_1') return 3;
  if (task === 'example_task_2') return 6;
  return 9;
}

function JobStatus({ job }: { job: Job }) {
  const { task, status, created_at } = job;
  const expectedSec = useMemo(() => expectedDurationSec(task), [task]);
  const createdAtMs = useMemo(
    () => new Date(created_at).getTime(),
    [created_at],
  );
  const [elapsedSec, setElapsedSec] = useState(() =>
    Math.max(0, Math.floor((Date.now() - createdAtMs) / 1000)),
  );

  useEffect(() => {
    if (status === 'completed' || status === 'failed') return;
    const interval = setInterval(() => {
      setElapsedSec(Math.max(0, Math.floor((Date.now() - createdAtMs) / 1000)));
    }, 1000);
    return () => clearInterval(interval);
  }, [status, createdAtMs]);

  const isActive = status === 'queued' || status === 'processing';
  const isDone = status === 'completed';
  const isFailed = status === 'failed';

  const barClassName = useMemo(() => {
    if (isActive) return 'bg-primary/10 text-primary animate-pulse';
    if (isDone) return 'bg-green-500/15 text-green-700 dark:text-green-400';
    if (isFailed) return 'bg-red-500/15 text-red-700 dark:text-red-400';
    return 'bg-muted text-muted-foreground';
  }, [isActive, isDone, isFailed]);

  const statusLabel = useMemo(() => {
    if (isDone)
      return {
        text: 'DONE',
        className: 'font-medium text-green-600 dark:text-green-400',
      };
    if (isFailed)
      return {
        text: 'Failed',
        className: 'font-medium text-red-600 dark:text-red-400',
      };
    return {
      text: `${elapsedSec}s (${expectedSec}s)`,
      className: 'tabular-nums',
    };
  }, [isDone, isFailed, elapsedSec, expectedSec]);

  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card px-4 py-3 shadow-sm transition-shadow">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div
          className={
            'flex h-9 min-w-[120px] items-center rounded-md px-3 font-medium text-card-foreground ' +
            barClassName
          }
        >
          <span className="truncate">{task}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {isActive && (
            <span
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"
              aria-hidden
            />
          )}
          <span className={statusLabel.className}>{statusLabel.text}</span>
        </div>
      </div>
    </div>
  );
}
