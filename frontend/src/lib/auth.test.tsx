import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './auth';
import * as authApi from '@/lib/api/auth';
import type { AuthUser } from '@/types/auth';

// --- Mocks -----------------------------------------------------------------
const replace = jest.fn();
let pathname = '/dashboard';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
  usePathname: () => pathname,
}));

jest.mock('@/lib/api/auth');
const mockedApi = authApi as jest.Mocked<typeof authApi>;

const TEC: AuthUser = {
  id: 2,
  email: 'tecnico1@oefa.gob.pe',
  nombre: 'Tec',
  apellido: 'Uno',
  rol: 'tecnico',
};
const COORD: AuthUser = {
  id: 3,
  email: 'coord1@oefa.gob.pe',
  nombre: 'Coord',
  apellido: 'Uno',
  rol: 'coordinador',
};

// Test harness component that surfaces context + drives actions.
function Consumer() {
  const { user, isAuthenticated, loading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="auth">{String(isAuthenticated)}</span>
      <span data-testid="user">{user?.email ?? 'none'}</span>
      <button onClick={() => login('e@x.com', 'pw')}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

function renderAuth() {
  return render(
    <AuthProvider>
      <Consumer />
    </AuthProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  pathname = '/dashboard';
});

describe('AuthProvider initial mount', () => {
  it('redirects to /login when there is no saved token', async () => {
    renderAuth();
    await waitFor(() =>
      expect(screen.getByTestId('loading')).toHaveTextContent('false'),
    );
    expect(replace).toHaveBeenCalledWith('/login');
    expect(screen.getByTestId('auth')).toHaveTextContent('false');
  });

  it('does not redirect from a public path when unauthenticated', async () => {
    pathname = '/login';
    renderAuth();
    await waitFor(() =>
      expect(screen.getByTestId('loading')).toHaveTextContent('false'),
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it('validates a saved token via fetchMe and hydrates the user', async () => {
    localStorage.setItem('token', 'good');
    mockedApi.fetchMe.mockResolvedValueOnce(COORD);
    renderAuth();
    await waitFor(() =>
      expect(screen.getByTestId('user')).toHaveTextContent(COORD.email),
    );
    expect(screen.getByTestId('auth')).toHaveTextContent('true');
  });

  it('refreshes when the saved token is invalid but a refresh token works', async () => {
    localStorage.setItem('token', 'stale');
    localStorage.setItem('refresh_token', 'r');
    mockedApi.fetchMe
      .mockRejectedValueOnce(new Error('Token invalido'))
      .mockResolvedValueOnce(COORD);
    mockedApi.refresh.mockResolvedValueOnce({
      access_token: 'fresh',
      token_type: 'bearer',
    });
    renderAuth();
    await waitFor(() =>
      expect(screen.getByTestId('user')).toHaveTextContent(COORD.email),
    );
    expect(localStorage.getItem('token')).toBe('fresh');
  });

  it('clears storage and redirects when token invalid and no refresh', async () => {
    localStorage.setItem('token', 'stale');
    mockedApi.fetchMe.mockRejectedValueOnce(new Error('Token invalido'));
    renderAuth();
    await waitFor(() =>
      expect(screen.getByTestId('loading')).toHaveTextContent('false'),
    );
    expect(localStorage.getItem('token')).toBeNull();
    expect(replace).toHaveBeenCalledWith('/login');
  });
});

describe('login', () => {
  it('stores tokens, sets the user, and routes a coordinador to /dashboard', async () => {
    renderAuth();
    await waitFor(() =>
      expect(screen.getByTestId('loading')).toHaveTextContent('false'),
    );
    mockedApi.login.mockResolvedValueOnce({
      access_token: 'tok',
      refresh_token: 'ref',
      token_type: 'bearer',
      usuario: COORD,
    });

    await act(async () => {
      screen.getByText('login').click();
    });

    expect(localStorage.getItem('token')).toBe('tok');
    expect(localStorage.getItem('refresh_token')).toBe('ref');
    expect(screen.getByTestId('user')).toHaveTextContent(COORD.email);
    expect(replace).toHaveBeenLastCalledWith('/dashboard');
  });

  it('routes a tecnico to /dashboard-tecnico', async () => {
    renderAuth();
    await waitFor(() =>
      expect(screen.getByTestId('loading')).toHaveTextContent('false'),
    );
    mockedApi.login.mockResolvedValueOnce({
      access_token: 'tok',
      refresh_token: null,
      token_type: 'bearer',
      usuario: TEC,
    });

    await act(async () => {
      screen.getByText('login').click();
    });

    expect(replace).toHaveBeenLastCalledWith('/dashboard-tecnico');
  });
});

describe('logout', () => {
  it('clears storage, drops the user, and redirects to /login', async () => {
    localStorage.setItem('token', 'good');
    mockedApi.fetchMe.mockResolvedValueOnce(COORD);
    renderAuth();
    await waitFor(() =>
      expect(screen.getByTestId('user')).toHaveTextContent(COORD.email),
    );

    await act(async () => {
      screen.getByText('logout').click();
    });

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(screen.getByTestId('user')).toHaveTextContent('none');
    expect(replace).toHaveBeenLastCalledWith('/login');
  });
});
