import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EquipoDetailPage from './page';
import * as lecturasApi from '@/lib/api/lecturas';
import * as opsApi from '@/lib/api/ops';
import * as healthApi from '@/lib/api/healthMonitor';
import type { Equipo } from '@/types/lectura';

let searchMode = 'view';
jest.mock('next/navigation', () => ({
  useParams: () => ({ deviceId: 'T-1' }),
  useSearchParams: () => ({
    get: (k: string) => (k === 'mode' ? searchMode : null),
  }),
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
}));

jest.mock('@/lib/api/lecturas');
jest.mock('@/lib/api/ops');
jest.mock('@/lib/api/healthMonitor');
const mL = lecturasApi as jest.Mocked<typeof lecturasApi>;
const mO = opsApi as jest.Mocked<typeof opsApi>;
const mH = healthApi as jest.Mocked<typeof healthApi>;

const equipo: Equipo = {
  id: 1,
  device_id: 'T-1',
  nombre: 'Est-A',
  tipo: 'analizador',
  ubicacion: 'Lima',
  estado: 'activo',
  serie: 'S1',
  codigo_interno: 'C1',
  modelo: 'M1',
  marca: 'Thermo',
  fecha_ingreso: '2026-01-01',
  rango_medicion: '0-1000',
  parametro_medicion: 'SO2',
  foto_equipo: null,
  datalogger_id: null,
  criticidad: 'media',
  fecha_registro: '2026-01-01T00:00:00Z',
  fecha_actualizacion: null,
};

beforeEach(() => {
  jest.clearAllMocks();
  searchMode = 'view';
  mL.fetchEquipo.mockResolvedValue(equipo);
  mL.fetchLecturas.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 100,
  });
  mO.fetchIncidencias.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 100,
  });
  mO.fetchCalibracionesOps.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 100,
  });
  mH.fetchHealthReadings.mockResolvedValue({ device_id: 'T-1', points: [] });
});

describe('EquipoDetailPage', () => {
  it('shows the loading state initially', () => {
    mL.fetchEquipo.mockReturnValueOnce(new Promise(() => {}));
    render(<EquipoDetailPage />);
    expect(screen.getByText(/Cargando.../i)).toBeInTheDocument();
  });

  it('renders the equipo heading + empty state', async () => {
    render(<EquipoDetailPage />);
    await waitFor(() =>
      expect(screen.getByText(/Equipo: Est-A/i)).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/Sin datos de salud disponibles/i),
    ).toBeInTheDocument();
  });

  it('switches tabs when clicked', async () => {
    const usr = userEvent.setup();
    render(<EquipoDetailPage />);
    await waitFor(() =>
      expect(screen.getByText(/Equipo: Est-A/i)).toBeInTheDocument(),
    );
    await usr.click(screen.getByRole('button', { name: 'Lecturas' }));
    expect(screen.getByText(/Lecturas de Sensores/i)).toBeInTheDocument();
    await usr.click(screen.getByRole('button', { name: 'Historial' }));
    expect(screen.getByText(/Mantenimientos Correctivos/i)).toBeInTheDocument();
    await usr.click(screen.getByRole('button', { name: 'Salud' }));
    // Salud tab renders detector breakdown panel; just ensure resumen text gone.
    expect(screen.queryByText(/Salud Predictiva$/i)).not.toBeInTheDocument();
  });

  it('renders edit form when mode=edit', async () => {
    searchMode = 'edit';
    render(<EquipoDetailPage />);
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /Guardar Cambios/i }),
      ).toBeInTheDocument(),
    );
  });

  it('renders error state when fetchEquipo fails', async () => {
    mL.fetchEquipo.mockRejectedValueOnce(new Error('not found'));
    render(<EquipoDetailPage />);
    expect(await screen.findByText('not found')).toBeInTheDocument();
  });
});
