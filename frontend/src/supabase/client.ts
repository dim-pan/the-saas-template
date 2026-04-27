import { createClient as createSupabaseClient } from '@supabase/supabase-js';

function getSupabaseConfig() {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
  const supabaseAnonKey = import.meta.env
    .VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY as string | undefined;

  if (!supabaseUrl) {
    throw new Error('Supabase URL is not set (VITE_SUPABASE_URL)');
  }

  if (!supabaseAnonKey) {
    throw new Error(
      'Supabase publishable key is not set (VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY)',
    );
  }

  return { supabaseUrl, supabaseAnonKey };
}

export function createClient() {
  const config = getSupabaseConfig();
  return createSupabaseClient(config.supabaseUrl, config.supabaseAnonKey, {
    auth: {
      flowType: 'pkce',
    },
  });
}

export const supabase = createClient();
