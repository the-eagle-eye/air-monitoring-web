import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import IncidenciasPage from './page';
import * as opsApi from '@/lib/api/ops';
import * as lecturasApi from '@/lib/api/lecturas';
import type { Incidencia, Usuario } from '@/types/ops';
import type { Equipo } from '@/types/lectura';

jest.mock('@/lib/api/ops');
jest.mock('@/lib/api/lecturas');
const mO = opsApi as jest.Mocked<typeof opsApi>;
const mL = lecturasApi as jest.Mocked<typeof lecturasApi>;

const incidencias: Incidencia[] = [
  {
    id: 1,
    device_id: 'T-1',
    tipo: 'correctiva',
    descripcion: 'x',
    estado: 'pendiente',
    prioridad: 'alta',
    responsable_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
  },
];

const equipos: Equipo[] = [
  { id: 1, device_id: 'T-1', nombre: 'Est-A' } as Equipo,
];

const usuarios: Usuario[] = [
  {
    id: 10,
    email: 't@x.com',
    nombre: 'Tec',
    apellido: 'U',
    rol: 'tecnico',
    estado: 'activo',
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  mO.fetchIncidencias.mockResolvedValue({
    items: incidencias,
    total: 1,
    page: 1,
    page_size: 50,
  });
  mO.fetchUsuarios.mockResolvedValue(usuarios);
  mL.fetchEquipos.mockResolvedValue(equipos);
});

describe('IncidenciasPage', () => {
  it('renders the list', async () => {
    render(<IncidenciasPage />);
    await screen.findAllByText('T-1');
    expect(
      screen.getByRole('heading', { name: /Incidencias Correctivas/i }),
    ).toBeInTheDocument();
  });

  it('toggles the create form', async () => {
    const usr = userEvent.setup();
    render(<IncidenciasPage />);
    await screen.findAllByText('T-1');
    await usr.click(screen.getByRole('button', { name: /Nueva Incidencia/i }));
    expect(
      await screen.findByRole('button', { name: /Crear Incidencia/i }),
    ).toBeInTheDocument();
  });

  it('surfaces an error on fetch failure', async () => {
    mO.fetchIncidencias.mockRejectedValueOnce(new Error('offline'));
    render(<IncidenciasPage />);
    expect(await screen.findByText('offline')).toBeInTheDocument();
  });
});
