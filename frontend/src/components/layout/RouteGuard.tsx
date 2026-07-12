'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';

// Routes accessible by role
const ROLE_ROUTES: Record<string, string[]> = {
  administrador: [
    '/',
    '/dashboard',
    '/equipos',
    '/incidencias',
    '/problemas',
    '/calibraciones',
    '/lecturas',
    '/repuestos',
    '/proveedores',
    '/usuarios',
    '/reportes',
  ],
  coordinador: [
    '/',
    '/dashboard',
    '/equipos',
    '/incidencias',
    '/problemas',
    '/calibraciones',
    '/lecturas',
    '/reportes',
  ],
  tecnico: [
    '/',
    '/dashboard-tecnico',
    '/equipos',
    '/incidencias',
    '/calibraciones',
    '/repuestos',
  ],
};

// Specific routes denied per role (checked before allowed routes)
const ROLE_DENY: Record<string, string[]> = {
  tecnico: ['/equipos/nuevo'],
};

// Default redirect per role when accessing forbidden route
const ROLE_DEFAULT: Record<string, string> = {
  administrador: '/dashboard',
  coordinador: '/dashboard',
  tecnico: '/dashboard-tecnico',
};

function isRouteAllowed(pathname: string, rol: string): boolean {
  const denied = ROLE_DENY[rol];
  if (denied?.some((route) => pathname === route)) return false;

  const allowed = ROLE_ROUTES[rol];
  if (!allowed) return true;
  return allowed.some((route) =>
    route === '/' ? pathname === '/' : pathname.startsWith(route),
  );
}

export default function RouteGuard({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, loading } = useAuth();

  useEffect(() => {
    if (loading || !isAuthenticated || !user) return;
    if (pathname === '/login') return;

    if (!isRouteAllowed(pathname, user.rol)) {
      router.replace(ROLE_DEFAULT[user.rol] ?? '/');
    }
  }, [pathname, user, isAuthenticated, loading, router]);

  return <>{children}</>;
}
