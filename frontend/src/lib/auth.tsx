'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import { useRouter, usePathname } from 'next/navigation';
import type { AuthUser } from '@/types/auth';
import * as authApi from '@/lib/api/auth';

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isAuthenticated: false,
  loading: true,
  login: async () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

const PUBLIC_PATHS = ['/login'];

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedRefresh = localStorage.getItem('refresh_token');

    if (!savedToken) {
      setLoading(false);
      if (!PUBLIC_PATHS.includes(pathname)) {
        router.replace('/login');
      }
      return;
    }

    // Validate token
    authApi
      .fetchMe(savedToken)
      .then((me) => {
        setToken(savedToken);
        setUser(me);
      })
      .catch(async () => {
        // Try refresh
        if (savedRefresh) {
          try {
            const refreshed = await authApi.refresh(savedRefresh);
            localStorage.setItem('token', refreshed.access_token);
            setToken(refreshed.access_token);
            const me = await authApi.fetchMe(refreshed.access_token);
            setUser(me);
            return;
          } catch {
            // refresh failed
          }
        }
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        if (!PUBLIC_PATHS.includes(pathname)) {
          router.replace('/login');
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loginFn = useCallback(
    async (email: string, password: string) => {
      const res = await authApi.login(email, password);
      localStorage.setItem('token', res.access_token);
      if (res.refresh_token) {
        localStorage.setItem('refresh_token', res.refresh_token);
      }
      if (res.usuario) {
        localStorage.setItem('user', JSON.stringify(res.usuario));
        setUser(res.usuario);
      }
      setToken(res.access_token);
      const rolDest =
        res.usuario?.rol === 'tecnico' ? '/dashboard-tecnico' : '/dashboard';
      router.replace(rolDest);
    },
    [router],
  );

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
    setToken(null);
    router.replace('/login');
  }, [router]);

  // Redirect to login if not authenticated and not on public path
  useEffect(() => {
    if (!loading && !token && !PUBLIC_PATHS.includes(pathname)) {
      router.replace('/login');
    }
  }, [loading, token, pathname, router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        loading,
        login: loginFn,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
