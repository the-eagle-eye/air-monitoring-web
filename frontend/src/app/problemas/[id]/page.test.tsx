import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProblemaDetailPage from './page';
import * as opsApi from '@/lib/api/ops';
import type { Problema, Incidencia } from '@/types/ops';

jest.mock('next/navigation', () => ({
  useParams: () => ({ id: '1' }),
}));

jest.mock('@/lib/api/ops');
const mO = opsApi as jest.Mocked<typeof opsApi>;

const problema: Problema = {
  id: 1,
  device_id: 'T-1',
  titulo: 'Sensor SO2 fallando',
  descripcion: 'Detalles del problema',
  estado: 'abierto',
  causa_raiz: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: null,
};

const incidencia: Incidencia = {
  id: 10,
  device_id: 'T-1',
  tipo: 'correctiva',
  descripcion: null,
  estado: 'pendiente',
  prioridad: 'alta',
  responsable_id: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: null,
};

beforeEach(() => {
  jest.clearAllMocks();
  mO.fetchProblema.mockResolvedValue(problema);
  mO.fetchProblemaIncidencias.mockResolvedValue([incidencia]);
});

describe('ProblemaDetailPage', () => {
  it('shows loading state initially', () => {
    mO.fetchProblema.mockReturnValue(new Promise(() => {}));
    render(<ProblemaDetailPage />);
    expect(screen.getByText(/Cargando.../i)).toBeInTheDocument();
  });

  it('renders the problema details + linked incidencias', async () => {
    render(<ProblemaDetailPage />);
    expect(
      await screen.findByRole('heading', { name: /Sensor SO2 fallando/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Incidentes vinculados \(1\)/i),
    ).toBeInTheDocument();
  });

  it('opens the edit form', async () => {
    const usr = userEvent.setup();
    render(<ProblemaDetailPage />);
    await screen.findByRole('heading', { name: /Sensor SO2 fallando/i });
    await usr.click(screen.getByRole('button', { name: /Editar/i }));
    expect(
      screen.getByRole('button', { name: /Guardar/i }),
    ).toBeInTheDocument();
  });

  it('shows an error on load failure', async () => {
    mO.fetchProblema.mockRejectedValueOnce(new Error('missing'));
    mO.fetchProblemaIncidencias.mockRejectedValueOnce(new Error('missing'));
    render(<ProblemaDetailPage />);
    expect(await screen.findByText('missing')).toBeInTheDocument();
  });
});
