import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { supabase } from '@/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { DigitCodeInput } from '@/components/auth/DigitCodeInput';

interface MagicLinkLoginFormProps {
  redirectTo: string;
}

export function MagicLinkLoginForm(props: MagicLinkLoginFormProps) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSendMagicLink = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    setOtpCode('');

    const result = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: props.redirectTo,
      },
    });

    if (result.error) {
      setErrorMessage(result.error.message);
      setIsLoading(false);
      return;
    }

    setIsSent(true);
    setIsLoading(false);
  };

  const handleVerifyOtp = async () => {
    setIsLoading(true);
    setErrorMessage(null);

    const result = await supabase.auth.verifyOtp({
      email,
      token: otpCode,
      type: 'email',
    });

    if (result.error) {
      setErrorMessage(result.error.message);
      setIsLoading(false);
      return;
    }

    await navigate({ to: '/' });
    setIsLoading(false);
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-2">
        <Label htmlFor="email" className="sr-only">
          Email
        </Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(value) => setEmail(value)}
          placeholder="enter your email"
        />
        {errorMessage && (
          <p className="text-sm text-destructive">{errorMessage}</p>
        )}
        {isSent && (
          <p className="text-sm text-muted-foreground">
            Check your email for the login link.
          </p>
        )}
      </div>

      {isSent ? (
        <div className="grid gap-2">
          <Label>6-digit code</Label>
          <DigitCodeInput
            numberOfDigits={6}
            value={otpCode}
            onChange={(value) => setOtpCode(value)}
            isDisabled={isLoading}
          />
        </div>
      ) : null}

      {isSent ? (
        <div className="flex flex-col gap-3">
          <Button
            isDisabled={isLoading || otpCode.length !== 6}
            onClick={() => {
              void handleVerifyOtp();
            }}
          >
            {isLoading ? 'Verifying…' : 'Continue'}
          </Button>
          <Button
            variant="link"
            className="h-auto p-0 justify-start"
            isDisabled={isLoading || email.length === 0}
            onClick={() => {
              void handleSendMagicLink();
            }}
          >
            Resend sign-in email
          </Button>
        </div>
      ) : (
        <Button
          isDisabled={isLoading || email.length === 0}
          onClick={() => {
            void handleSendMagicLink();
          }}
        >
          {isLoading ? 'Sending…' : 'Continue'}
        </Button>
      )}
    </div>
  );
}
