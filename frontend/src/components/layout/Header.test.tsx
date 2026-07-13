import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Header from './Header';
import type { AuthUser } from '@/types/auth';

const logout = jest.fn();
let pathname = '/dashboard';
let user: AuthUser | null = null;
let isAuthenticated = false;

jest.mock('next/navigation', () => ({
  usePathname: () => pathname,
}));

jest.mock('@/lib/auth', () => ({
  useAuth: () => ({ user, isAuthenticated, logout }),
}));

function u(rol: string, overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 1,
    email: 'a@x.com',
    nombre: 'A',
    apellido: 'B',
    rol,
    ...overrides,
  };
}

function setAuth(next: AuthUser | null) {
  user = next;
  isAuthenticated = next != null;
}

beforeEach(() => {
  logout.mockClear();
  pathname = '/dashboard';
  setAuth(null);
});

describe('Header — nav by role', () => {
  it('shows admin-only Administracion dropdown with Repuestos/Proveedores/Usuarios', () => {
    setAuth(u('administrador'));
    render(<Header />);
    expect(screen.getByText('Administracion')).toBeInTheDocument();
    // Dropdown items only visible when opened. Just assert the dropdown label exists.
    expect(screen.getByText('Operaciones')).toBeInTheDocument();
  });

  it('coordinador sees Reportes inside Operaciones and no Administracion dropdown', () => {
    setAuth(u('coordinador'));
    render(<Header />);
    expect(screen.queryByText('Administracion')).not.toBeInTheDocument();
    expect(screen.getByText('Operaciones')).toBeInTheDocument();
    expect(screen.queryByText('Lecturas')).toBeInTheDocument();
  });

  it('tecnico hides Lecturas and shows a plain Repuestos link (not a dropdown)', () => {
    setAuth(u('tecnico'));
    render(<Header />);
    expect(screen.queryByText('Lecturas')).not.toBeInTheDocument();
    // adminItems has just one entry → rendered as a NavLink
    const repuestos = screen.getByText('Repuestos');
    expect(repuestos.closest('a')?.getAttribute('href')).toBe('/repuestos');
  });

  it('tecnico Dashboard link goes to /dashboard-tecnico', () => {
    setAuth(u('tecnico'));
    render(<Header />);
    const link = screen.getByText('Dashboard').closest('a');
    expect(link?.getAttribute('href')).toBe('/dashboard-tecnico');
  });

  it('coordinador Dashboard link goes to /dashboard', () => {
    setAuth(u('coordinador'));
    render(<Header />);
    const link = screen.getByText('Dashboard').closest('a');
    expect(link?.getAttribute('href')).toBe('/dashboard');
  });
});

describe('Header — user chip + logout', () => {
  it('does not render the user chip when unauthenticated', () => {
    render(<Header />);
    expect(screen.queryByText('Salir')).not.toBeInTheDocument();
  });

  it('renders the user name and role label when authenticated', () => {
    setAuth(u('administrador', { nombre: 'Ana', apellido: 'Perez' }));
    render(<Header />);
    expect(screen.getByText('Ana Perez')).toBeInTheDocument();
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('falls back to raw rol string when not mapped', () => {
    setAuth(u('otro-rol'));
    render(<Header />);
    expect(screen.getByText('otro-rol')).toBeInTheDocument();
  });

  it('calls logout when the Salir button is clicked', async () => {
    setAuth(u('coordinador'));
    render(<Header />);
    await userEvent.click(screen.getByText('Salir'));
    expect(logout).toHaveBeenCalled();
  });
});

describe('Header — Operaciones dropdown open/close', () => {
  it('opens the dropdown, shows items, and links to correct routes', async () => {
    setAuth(u('coordinador'));
    const usr = userEvent.setup();
    render(<Header />);
    await usr.click(screen.getByText('Operaciones'));
    expect(screen.getByText('Incidencias')).toBeInTheDocument();
    expect(screen.getByText('Problemas')).toBeInTheDocument();
    const cal = screen.getByText('Calibraciones').closest('a');
    expect(cal?.getAttribute('href')).toBe('/calibraciones');
  });

  it('closes the dropdown when clicking outside', async () => {
    setAuth(u('coordinador'));
    const usr = userEvent.setup();
    render(<Header />);
    await usr.click(screen.getByText('Operaciones'));
    expect(screen.getByText('Incidencias')).toBeInTheDocument();
    await act(async () => {
      document.body.dispatchEvent(
        new MouseEvent('mousedown', { bubbles: true }),
      );
    });
    expect(screen.queryByText('Incidencias')).not.toBeInTheDocument();
  });

  it('closes the dropdown after selecting an item', async () => {
    setAuth(u('coordinador'));
    const usr = userEvent.setup();
    render(<Header />);
    await usr.click(screen.getByText('Operaciones'));
    await usr.click(screen.getByText('Problemas'));
    expect(screen.queryByText('Incidencias')).not.toBeInTheDocument();
  });
});

describe('Header — active link highlighting', () => {
  it('marks the Inicio link active only when pathname === "/"', () => {
    setAuth(u('coordinador'));
    pathname = '/';
    render(<Header />);
    const inicio = screen.getByText('Inicio').closest('a')!;
    expect(inicio.className).toContain('bg-zinc-100');
  });

  it('does NOT mark Inicio active on nested routes', () => {
    setAuth(u('coordinador'));
    pathname = '/dashboard';
    render(<Header />);
    const inicio = screen.getByText('Inicio').closest('a')!;
    expect(inicio.className).not.toContain('bg-zinc-100');
  });
});
