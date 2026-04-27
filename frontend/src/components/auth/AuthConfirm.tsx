import { useEffect, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { supabase } from '@/supabase/client';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

function getSearchParam(param: string) {
  return new URLSearchParams(window.location.search).get(param);
}

export function AuthConfirm() {
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isAlive = true;

    const handleConfirm = async () => {
      try {
        const tokenHash = getSearchParam('token_hash');
        const type = getSearchParam('type');

        if (!tokenHash) {
          throw new Error('Missing token_hash');
        }
        if (type !== 'email') {
          throw new Error('Invalid confirmation type');
        }

        const result = await supabase.auth.verifyOtp({
          token_hash: tokenHash,
          type: 'email',
        });
        if (result.error) {
          throw result.error;
        }

        const redirectTo = getSearchParam('redirect');
        if (redirectTo) {
          window.location.assign(redirectTo);
          return;
        }

        await navigate({ to: '/' });
      } catch (error) {
        if (!isAlive) {
          return;
        }
        const message =
          error instanceof Error ? error.message : 'Auth confirm failed';
        setErrorMessage(message);
      }
    };

    void handleConfirm();

    return () => {
      isAlive = false;
    };
  }, [navigate]);

  return (
    <div className="p-6 max-w-lg mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Signing you in…</CardTitle>
          <CardDescription>
            {errorMessage
              ? 'Something went wrong.'
              : 'Please wait while we finish logging you in.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {errorMessage ? (
            <p className="text-sm text-destructive">{errorMessage}</p>
          ) : (
            <p className="text-sm text-muted-foreground">
              You can close this tab if nothing happens.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
