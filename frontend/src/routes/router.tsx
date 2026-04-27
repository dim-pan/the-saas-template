import { createRootRoute, createRoute, redirect } from '@tanstack/react-router';
import { Outlet } from '@tanstack/react-router';
import { Home } from './home';
import { About } from './about';
import { Login } from './login';
import { Accounts } from './accounts';
import { Pricing } from './pricing';
import { AuthConfirmRoute } from './auth-confirm';
import { supabase } from '@/supabase/client';
import { LeftNav } from '@/components/layout/LeftNav';

function RootLayout() {
  return (
    <>
      <Outlet />
      {/* <TanStackRouterDevtools /> */}
    </>
  );
}

export const ROOT_ROUTE = createRootRoute({
  component: RootLayout,
});

const protectedLayout = createRoute({
  getParentRoute: () => ROOT_ROUTE,
  id: 'protected',
  beforeLoad: async ({ location }) => {
    const result = await supabase.auth.getSession();
    if (result.error || !result.data.session) {
      return redirect({
        to: '/login',
        search: {
          redirect: location.href,
        },
      });
    }
  },
  component: () => (
    <div className="min-h-screen flex bg-background">
      <LeftNav />
      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  ),
});

const home = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/',
  component: Home,
});

const about = createRoute({
  getParentRoute: () => ROOT_ROUTE,
  path: '/about',
  component: About,
});

const login = createRoute({
  getParentRoute: () => ROOT_ROUTE,
  path: '/login',
  component: Login,
});

const accounts = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/accounts',
  component: Accounts,
});

const pricing = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/upgrade',
  component: Pricing,
});

const authConfirm = createRoute({
  getParentRoute: () => ROOT_ROUTE,
  path: '/auth/confirm',
  component: AuthConfirmRoute,
});

export const ROUTES = [
  protectedLayout.addChildren([home, accounts, pricing]),
  about,
  login,
  authConfirm,
];
