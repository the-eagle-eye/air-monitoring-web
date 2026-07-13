import { render, screen, waitFor } from '@testing-library/react';
import DashboardTecnicoPage from './page';
import * as opsApi from '@/lib/api/ops';
import * as lecturasApi from '@/lib/api/lecturas';
import * as healthApi from '@/lib/api/healthMonitor';
import type { Incidencia, Repuesto } from '@/types/ops';
import type { Equipo } from '@/types/lectura';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: () => '/dashboard-tecnico',
}));

jest.mock('@/lib/api/ops');
jest.mock('@/lib/api/lecturas');
jest.mock('@/lib/api/healthMonitor');
const mO = opsApi as jest.Mocked<typeof opsApi>;
const mL = lecturasApi as jest.Mocked<typeof lecturasApi>;
const mH = healthApi as jest.Mocked<typeof healthApi>;

const inc: Incidencia = {
  id: 1,
  device_id: 'T-1',
  tipo: 'correctiva',
  descripcion: 'un fallo detallado',
  estado: 'pendiente',
  prioridad: 'alta',
  responsable_id: 10,
  created_at: new Date().toISOString(),
  updated_at: null,
};

const finalizadaVieja: Incidencia = {
  ...inc,
  id: 2,
  estado: 'finalizado',
  mantenimiento_correctivo: {
    id: 1,
    incidencia_id: 2,
    diagnostico: null,
    acciones_realizadas: null,
    conclusion: null,
    fecha_ejecucion: null,
    repuestos: [
      { id: 1, nombre: 'Filtro', categoria: 'Filtros y Consumibles' },
    ],
    adjuntos: [],
    created_at: '2026-01-01',
  },
};

const equipos: Equipo[] = [
  { id: 1, device_id: 'T-1', nombre: 'Est-A', tipo: 'analizador' } as Equipo,
];

const repuestos: Repuesto[] = [
  {
    id: 1,
    nombre: 'Filtro',
    categoria: 'Filtros y Consumibles',
    estado: 'activo',
    created_at: '2026-01-01',
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  mO.fetchIncidencias.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 50,
  });
  mO.fetchRepuestos.mockResolvedValue([]);
  mL.fetchEquipos.mockResolvedValue([]);
  mH.fetchHealthStates.mockResolvedValue({});
});

describe('DashboardTecnicoPage', () => {
  it('shows the loading state initially', () => {
    mO.fetchIncidencias.mockReturnValue(new Promise(() => {}));
    render(<DashboardTecnicoPage />);
    expect(screen.getByText(/Cargando dashboard.../i)).toBeInTheDocument();
  });

  it('renders the "Mi Panel de Trabajo" heading after load', async () => {
    render(<DashboardTecnicoPage />);
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /Mi Panel de Trabajo/i }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/No tienes incidencias activas asignadas/i),
    ).toBeInTheDocument();
  });

  it('renders active incidencias, equipos with health, and repuestos', async () => {
    mO.fetchIncidencias.mockImplementation(
      (params: Parameters<typeof opsApi.fetchIncidencias>[0] = {}) => {
        const { estado } = params;
        if (estado === 'pendiente')
          return Promise.resolve({
            items: [inc],
            total: 1,
            page: 1,
            page_size: 50,
          });
        if (estado === 'finalizado')
          return Promise.resolve({
            items: [finalizadaVieja],
            total: 1,
            page: 1,
            page_size: 50,
          });
        return Promise.resolve({ items: [], total: 0, page: 1, page_size: 50 });
      },
    );
    mL.fetchEquipos.mockResolvedValue(equipos);
    mO.fetchRepuestos.mockResolvedValue(repuestos);
    mH.fetchHealthStates.mockResolvedValue({
      'T-1': {
        device_id: 'T-1',
        health_state: 'SANO',
        last_recon_error: 0.1,
        theta: 0.2,
        hours_since_prev: 2.5,
        updated_at: '2026-01-01',
      },
    });

    render(<DashboardTecnicoPage />);
    await screen.findByRole('heading', { name: /Mi Panel de Trabajo/i });
    await waitFor(() =>
      expect(screen.getAllByText('T-1').length).toBeGreaterThan(0),
    );
    // KPI card "Pendientes" reflects the fetched pendientes.
    expect(screen.getByText(/Pendientes/i)).toBeInTheDocument();
  });
});
