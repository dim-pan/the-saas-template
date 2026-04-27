import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { PropsWithChildren } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '@/supabase/client';

export type SignOutScope = 'global' | 'local' | 'others';

export interface SignOutOptions {
  scope?: SignOutScope;
}

interface AuthState {
  isLoading: boolean;
  session: Session | null;
  user: User | null;
  refreshSession: () => Promise<void>;
  signOut: (options?: SignOutOptions) => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) {
    throw new Error('useAuth must be used within <AuthProvider>');
  }
  return auth;
}

async function getSessionFromSupabase() {
  const result = await supabase.auth.getSession();
  if (result.error) {
    throw result.error;
  }
  return result.data.session;
}

export function AuthProvider(props: PropsWithChildren) {
  const [isLoading, setIsLoading] = useState(true);
  const [session, setSession] = useState<Session | null>(null);

  const refreshSession = async () => {
    const nextSession = await getSessionFromSupabase();
    setSession(nextSession);
  };

  const signOut = async (options?: SignOutOptions) => {
    const result = await supabase.auth.signOut(options);
    if (result.error) {
      throw result.error;
    }
  };

  useEffect(() => {
    let isAlive = true;

    async function init() {
      try {
        const nextSession = await getSessionFromSupabase();
        if (isAlive) {
          setSession(nextSession);
        }
      } finally {
        if (isAlive) {
          setIsLoading(false);
        }
      }
    }

    void init();

    const subscription = supabase.auth.onAuthStateChange(
      (_event, nextSession) => {
        setSession(nextSession);
        setIsLoading(false);
      },
    );

    return () => {
      isAlive = false;
      subscription.data.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthState>(() => {
    return {
      isLoading,
      session,
      user: session?.user ?? null,
      refreshSession,
      signOut,
    };
  }, [isLoading, session]);

  return (
    <AuthContext.Provider value={value}>{props.children}</AuthContext.Provider>
  );
}
