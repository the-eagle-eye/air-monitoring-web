import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CalibracionesPage from './page';
import * as opsApi from '@/lib/api/ops';
import * as lecturasApi from '@/lib/api/lecturas';
import type { CalibracionOps, Proveedor } from '@/types/ops';
import type { Equipo } from '@/types/lectura';

let authRol = 'coordinador';
jest.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'a@x.com', nombre: 'A', apellido: 'B', rol: authRol },
  }),
}));

jest.mock('@/lib/api/ops');
jest.mock('@/lib/api/lecturas');
const mO = opsApi as jest.Mocked<typeof opsApi>;
const mL = lecturasApi as jest.Mocked<typeof lecturasApi>;

const calibraciones: CalibracionOps[] = [
  {
    id: 1,
    incidencia_id: null,
    device_id: 'T-1',
    fecha_calibracion: null,
    nota: 'x',
    certificado_url: null,
    proveedor_id: null,
    estado: 'pendiente',
    incidencia_estado: null,
    created_at: '2026-01-01T00:00:00Z',
  },
];

const equipos: Equipo[] = [
  { id: 1, device_id: 'T-1', nombre: 'Est-A' } as Equipo,
];

const proveedores: Proveedor[] = [
  { id: 1, nombre: 'AcmeCal', estado: 'activo' },
];

beforeEach(() => {
  jest.clearAllMocks();
  authRol = 'coordinador';
  mO.fetchCalibracionesOps.mockResolvedValue({
    items: calibraciones,
    total: 1,
    page: 1,
    page_size: 50,
  });
  mO.fetchProveedores.mockResolvedValue(proveedores);
  mL.fetchEquipos.mockResolvedValue(equipos);
});

describe('CalibracionesPage', () => {
  it('renders the list', async () => {
    render(<CalibracionesPage />);
    expect(await screen.findByText(/Calibraciones/i)).toBeInTheDocument();
    // Wait for row render.
    await screen.findAllByText('T-1');
  });

  it('opens and submits the create form for a coordinador', async () => {
    mO.createCalibracion.mockResolvedValueOnce({ id: 2 } as never);
    const usr = userEvent.setup();
    render(<CalibracionesPage />);
    await screen.findAllByText('T-1');
    await usr.click(screen.getByRole('button', { name: /Nueva Calibracion/i }));
    await usr.click(screen.getByRole('button', { name: /^Crear/i }));
    await waitFor(() =>
      expect(mO.createCalibracion).toHaveBeenCalledWith(
        expect.objectContaining({ device_id: 'T-1' }),
      ),
    );
  });

  it('hides "Nueva Calibracion" for a técnico', async () => {
    authRol = 'tecnico';
    render(<CalibracionesPage />);
    await screen.findAllByText('T-1');
    expect(
      screen.queryByRole('button', { name: /Nueva Calibracion/i }),
    ).not.toBeInTheDocument();
  });
});
