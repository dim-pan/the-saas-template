import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/components/auth/AuthProvider';
import type { SignOutScope } from '@/components/auth/AuthProvider';

export interface SignOutButtonProps {
  scope?: SignOutScope;
  className?: string;
}

export function SignOutButton(props: SignOutButtonProps) {
  const auth = useAuth();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const isDisabled = auth.isLoading || !auth.user || isLoading;

  const handleClick = async () => {
    setIsLoading(true);
    try {
      await auth.signOut({ scope: props.scope });
      await navigate({ to: '/login' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      variant="secondary"
      className={props.className}
      isDisabled={isDisabled}
      onClick={() => {
        void handleClick();
      }}
    >
      {isLoading ? 'Signing out…' : 'Sign out'}
    </Button>
  );
}
