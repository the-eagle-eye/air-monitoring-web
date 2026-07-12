'use client';

import { usePathname } from 'next/navigation';
import { AuthProvider } from '@/lib/auth';
import Header from '@/components/layout/Header';
import RouteGuard from '@/components/layout/RouteGuard';

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';

  return (
    <AuthProvider>
      {!isLoginPage && <Header />}
      <RouteGuard>{children}</RouteGuard>
    </AuthProvider>
  );
}
