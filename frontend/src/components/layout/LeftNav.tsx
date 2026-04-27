import { Link } from '@tanstack/react-router';
import { useAuth } from '@/components/auth/AuthProvider';
import { SignOutButton } from '@/components/auth/SignOutButton';

export function LeftNav() {
  const auth = useAuth();

  const userLabel = auth.user?.email ?? auth.user?.id ?? 'Signed in';

  return (
    <aside className="w-64 shrink-0 border-r border-border bg-surface">
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="h-14 flex items-center px-4 border-b border-border">
          <p className="text-sm font-semibold text-foreground">Logo</p>
        </div>

        {/* Middle */}
        <div className="flex-1 p-3">
          <nav className="flex flex-col gap-1">
            <Link
              to="/"
              className="rounded-md px-3 py-2 text-sm text-foreground hover:bg-muted [&.active]:bg-muted [&.active]:font-medium"
            >
              Home
            </Link>
            <Link
              to="/accounts"
              className="rounded-md px-3 py-2 text-sm text-foreground hover:bg-muted [&.active]:bg-muted [&.active]:font-medium"
            >
              Account
            </Link>
            <Link
              to="/upgrade"
              className="rounded-md px-3 py-2 text-sm text-foreground hover:bg-muted [&.active]:bg-muted [&.active]:font-medium"
            >
              Pricing
            </Link>
          </nav>
        </div>

        {/* Footer */}
        <div className="border-t border-border p-4">
          <p className="text-sm font-medium text-foreground truncate">
            {userLabel}
          </p>
          <div className="mt-2">
            <SignOutButton scope="local" />
          </div>
        </div>
      </div>
    </aside>
  );
}
