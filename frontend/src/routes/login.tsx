import { MagicLinkLoginForm } from '@/components/auth/MagicLinkLoginForm';

function getSearchParam(param: string) {
  return new URLSearchParams(window.location.search).get(param);
}

export function Login() {
  const redirectUrl = getSearchParam('redirect');
  const authConfirmUrl = new URL('/auth/confirm', window.location.origin);
  if (redirectUrl) {
    authConfirmUrl.searchParams.set('redirect', redirectUrl);
  }

  return (
    <div className="min-h-screen flex flex-col-reverse sm:flex-row ">
      <div className="flex-1 flex items-start sm:items-center">
        <div className="w-full mx-auto px-12 py-8 sm:px-4 md:max-w-sm">
          <h1 className="text-3xl font-semibold text-foreground sm:text-4xl">
            Welcome to The SaaS Template
          </h1>
          <p className="text-sm text-muted-foreground pb-4">
            Sign in to continue.
          </p>
          <MagicLinkLoginForm redirectTo={authConfirmUrl.toString()} />
        </div>
      </div>
      <div className="h-[55vh] sm:flex-1 sm:h-screen w-full bg-primary/20 rounded-b-4xl sm:rounded-l-4xl sm:rounded-br-none">
        <div className="h-full w-full p-5 object-contain flex items-end justify-center"></div>
      </div>
    </div>
  );
}
