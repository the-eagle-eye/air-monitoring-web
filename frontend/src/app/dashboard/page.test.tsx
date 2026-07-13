import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from './page';
import * as dashboardApi from '@/lib/api/dashboard';
import * as opsApi from '@/lib/api/ops';
import * as healthApi from '@/lib/api/healthMonitor';
import type { Equipo } from '@/types/lectura';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: () => '/dashboard',
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

jest.mock('@/lib/api/dashboard');
jest.mock('@/lib/api/ops');
jest.mock('@/lib/api/healthMonitor');
const mD = dashboardApi as jest.Mocked<typeof dashboardApi>;
const mO = opsApi as jest.Mocked<typeof opsApi>;
const mH = healthApi as jest.Mocked<typeof healthApi>;

const equipos: Equipo[] = [
  { id: 1, device_id: 'T-1', nombre: 'Est-A' } as Equipo,
];

beforeEach(() => {
  jest.clearAllMocks();
  authRol = 'administrador';
  mD.fetchDashboardData.mockResolvedValue({ equipos });
  mD.fetchEquipoLecturas.mockResolvedValue([]);
  mH.fetchHealthStates.mockResolvedValue({});
  mH.fetchHealthReadings.mockResolvedValue({ device_id: 'T-1', points: [] });
  mO.fetchIncidencias.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 50,
  });
  mO.fetchCalibracionesOps.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 100,
  });
  mO.fetchReincidentes.mockResolvedValue({
    dias: 90,
    min_correctivas: 3,
    items: [],
  });
  mO.fetchProblemasResumen.mockResolvedValue({
    por_estado: {},
    abiertos: 0,
    total: 0,
  });
});

describe('DashboardPage', () => {
  it('shows the loading state initially', () => {
    mD.fetchDashboardData.mockReturnValueOnce(new Promise(() => {}));
    render(<DashboardPage />);
    expect(screen.getByText(/Cargando dashboard.../i)).toBeInTheDocument();
  });

  it('renders the dashboard heading after data loads', async () => {
    render(<DashboardPage />);
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /Dashboard de Monitoreo/i }),
      ).toBeInTheDocument(),
    );
  });

  it('renders an error banner when fetch fails', async () => {
    mD.fetchDashboardData.mockRejectedValueOnce(new Error('boom'));
    render(<DashboardPage />);
    expect(await screen.findByText('boom')).toBeInTheDocument();
  });

  it('renders with tecnico rol (canCrearProblema=false)', async () => {
    authRol = 'tecnico';
    render(<DashboardPage />);
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /Dashboard de Monitoreo/i }),
      ).toBeInTheDocument(),
    );
  });
});
