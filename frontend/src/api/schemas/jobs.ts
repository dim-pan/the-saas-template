import { z } from 'zod';

export const JobSchema = z.object({
  id: z.uuid(),
  organization_id: z.uuid(),
  user_id: z.uuid(),
  task: z.string(),
  data: z.record(z.string(), z.unknown()),
  status: z.enum(['queued', 'processing', 'completed', 'failed']),
  created_at: z.string(),
  updated_at: z.string().nullable().optional(),
  submitted_at: z.string(),
  finished_at: z.string().nullable().optional(),
});

export type Job = z.infer<typeof JobSchema>;

export const CreateJobRequestSchema = z.object({
  task: z.string(),
  data: z.record(z.string(), z.unknown()).optional(),
});

export type CreateJobRequest = z.infer<typeof CreateJobRequestSchema>;
