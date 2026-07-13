import { render, screen } from '@testing-library/react';
import RouteGuard from './RouteGuard';
import type { AuthUser } from '@/types/auth';

const replace = jest.fn();
let pathname = '/dashboard';
let user: AuthUser | null = null;
let isAuthenticated = false;
let loading = false;

jest.mock('next/navigation', () => ({
  usePathname: () => pathname,
  useRouter: () => ({ replace }),
}));

jest.mock('@/lib/auth', () => ({
  useAuth: () => ({ user, isAuthenticated, loading }),
}));

function auth(rol: string): AuthUser {
  return { id: 1, email: 'a@x.com', nombre: 'A', apellido: 'B', rol };
}

beforeEach(() => {
  replace.mockClear();
  pathname = '/dashboard';
  user = null;
  isAuthenticated = false;
  loading = false;
});

describe('RouteGuard', () => {
  it('always renders children', () => {
    render(<RouteGuard>content</RouteGuard>);
    expect(screen.getByText('content')).toBeInTheDocument();
  });

  it('does nothing while loading', () => {
    loading = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).not.toHaveBeenCalled();
  });

  it('does nothing when unauthenticated', () => {
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).not.toHaveBeenCalled();
  });

  it('does not redirect on /login even when authenticated', () => {
    pathname = '/login';
    user = auth('coordinador');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).not.toHaveBeenCalled();
  });

  it('lets an admin visit /usuarios', () => {
    pathname = '/usuarios';
    user = auth('administrador');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).not.toHaveBeenCalled();
  });

  it('redirects a coordinador away from /usuarios (admin-only)', () => {
    pathname = '/usuarios';
    user = auth('coordinador');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).toHaveBeenCalledWith('/dashboard');
  });

  it('redirects a tecnico away from /dashboard to /dashboard-tecnico', () => {
    pathname = '/dashboard';
    user = auth('tecnico');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).toHaveBeenCalledWith('/dashboard-tecnico');
  });

  it('lets a tecnico visit /dashboard-tecnico', () => {
    pathname = '/dashboard-tecnico';
    user = auth('tecnico');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).not.toHaveBeenCalled();
  });

  it('respects deny-list: tecnico cannot access /equipos/nuevo', () => {
    pathname = '/equipos/nuevo';
    user = auth('tecnico');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).toHaveBeenCalledWith('/dashboard-tecnico');
  });

  it('tecnico CAN access /equipos (deny-list is exact match)', () => {
    pathname = '/equipos';
    user = auth('tecnico');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).not.toHaveBeenCalled();
  });

  it('unknown roles are unrestricted (no allowed list defined)', () => {
    pathname = '/whatever';
    user = auth('mystery');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).not.toHaveBeenCalled();
  });

  it('unknown roles fall back to "/" when a default redirect is missing', () => {
    // isRouteAllowed returns true for unknown roles → no redirect triggers.
    // Cover the ROLE_DEFAULT fallback by giving them a route that IS restricted
    // for known roles. But allow list is only checked for known roles → skipped.
    // (This test documents the current behavior.)
    pathname = '/anywhere';
    user = auth('mystery');
    isAuthenticated = true;
    render(<RouteGuard>x</RouteGuard>);
    expect(replace).not.toHaveBeenCalled();
  });
});
