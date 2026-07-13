import { render, screen } from '@testing-library/react';
import ClientLayout from './ClientLayout';

let pathname = '/dashboard';

jest.mock('next/navigation', () => ({
  usePathname: () => pathname,
  useRouter: () => ({ replace: jest.fn() }),
}));

jest.mock('@/lib/auth', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="auth-provider">{children}</div>
  ),
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    loading: false,
    logout: jest.fn(),
  }),
}));

jest.mock('@/components/layout/Header', () => ({
  __esModule: true,
  default: () => <div data-testid="header" />,
}));

jest.mock('@/components/layout/RouteGuard', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

beforeEach(() => {
  pathname = '/dashboard';
});

describe('ClientLayout', () => {
  it('renders Header + children on non-login routes', () => {
    render(
      <ClientLayout>
        <div>child</div>
      </ClientLayout>,
    );
    expect(screen.getByTestId('header')).toBeInTheDocument();
    expect(screen.getByText('child')).toBeInTheDocument();
    expect(screen.getByTestId('auth-provider')).toBeInTheDocument();
  });

  it('omits the Header on /login', () => {
    pathname = '/login';
    render(
      <ClientLayout>
        <div>child</div>
      </ClientLayout>,
    );
    expect(screen.queryByTestId('header')).not.toBeInTheDocument();
    expect(screen.getByText('child')).toBeInTheDocument();
  });
});
