import { render, screen, waitFor } from '@testing-library/react';
import EquiposPage from './page';
import * as lecturasApi from '@/lib/api/lecturas';
import type { Equipo } from '@/types/lectura';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: () => '/equipos',
}));

let authRol = 'administrador';
jest.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'a@x.com', nombre: 'A', apellido: 'B', rol: authRol },
    isAuthenticated: true,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

jest.mock('@/lib/api/lecturas');
const mL = lecturasApi as jest.Mocked<typeof lecturasApi>;

const equipos: Equipo[] = [
  { id: 1, device_id: 'T-1', nombre: 'Est-A' } as Equipo,
];

beforeEach(() => {
  jest.clearAllMocks();
  authRol = 'administrador';
  mL.fetchEquipos.mockResolvedValue(equipos);
  mL.fetchEquiposPendientes.mockResolvedValue([]);
});

describe('EquiposPage', () => {
  it('shows "Nuevo Equipo" link for administrador', async () => {
    render(<EquiposPage />);
    await waitFor(() => expect(mL.fetchEquipos).toHaveBeenCalled());
    expect(
      screen.getByRole('link', { name: /Nuevo Equipo/i }),
    ).toBeInTheDocument();
  });

  it('hides "Nuevo Equipo" for tecnico', async () => {
    authRol = 'tecnico';
    render(<EquiposPage />);
    await waitFor(() => expect(mL.fetchEquipos).toHaveBeenCalled());
    expect(
      screen.queryByRole('link', { name: /Nuevo Equipo/i }),
    ).not.toBeInTheDocument();
  });

  it('renders the loading state initially', () => {
    mL.fetchEquipos.mockReturnValueOnce(new Promise(() => {}));
    render(<EquiposPage />);
    expect(screen.getByText(/Cargando.../i)).toBeInTheDocument();
  });

  it('shows an error banner when fetch fails', async () => {
    mL.fetchEquipos.mockRejectedValueOnce(new Error('offline'));
    render(<EquiposPage />);
    expect(await screen.findByText('offline')).toBeInTheDocument();
  });
});
