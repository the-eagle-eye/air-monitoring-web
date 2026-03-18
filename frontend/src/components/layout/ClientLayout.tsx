'use client';

import { usePathname } from 'next/navigation';
import { AuthProvider } from '@/lib/auth';
import Header from '@/components/layout/Header';

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
      {children}
    </AuthProvider>
  );
}
