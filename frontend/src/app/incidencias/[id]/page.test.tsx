import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import IncidenciaDetailPage from './page';
import * as opsApi from '@/lib/api/ops';
import type { Incidencia, Usuario, Repuesto } from '@/types/ops';

jest.mock('next/navigation', () => ({
  useParams: () => ({ id: '1' }),
  useRouter: () => ({ back: jest.fn(), push: jest.fn(), replace: jest.fn() }),
}));

let authRol = 'coordinador';
jest.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'a@x.com', nombre: 'A', apellido: 'B', rol: authRol },
    isAuthenticated: true,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

jest.mock('@/lib/api/ops');
const mO = opsApi as jest.Mocked<typeof opsApi>;

const usuarios: Usuario[] = [
  {
    id: 10,
    email: 't@x.com',
    nombre: 'Tec',
    apellido: 'Uno',
    rol: 'tecnico',
    estado: 'activo',
  },
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

function makeInc(overrides: Partial<Incidencia> = {}): Incidencia {
  return {
    id: 1,
    device_id: 'T-1',
    tipo: 'correctiva',
    descripcion: 'algo',
    estado: 'pendiente',
    prioridad: 'alta',
    responsable_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
    ...overrides,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  authRol = 'coordinador';
  mO.fetchIncidencia.mockResolvedValue(makeInc());
  mO.fetchUsuarios.mockResolvedValue(usuarios);
  mO.fetchRepuestos.mockResolvedValue(repuestos);
  mO.fetchProblemas.mockResolvedValue({ items: [], total: 0 });
  mO.updateIncidencia.mockResolvedValue({} as never);
  mO.submitMantenimiento.mockResolvedValue({} as never);
  mO.linkIncidenciaProblema.mockResolvedValue({} as never);
});

describe('IncidenciaDetailPage', () => {
  it('shows the loading state initially', () => {
    mO.fetchIncidencia.mockReturnValue(new Promise(() => {}));
    render(<IncidenciaDetailPage />);
    expect(screen.getByText(/Cargando.../i)).toBeInTheDocument();
  });

  it('renders the incidencia details', async () => {
    render(<IncidenciaDetailPage />);
    expect(
      await screen.findByRole('heading', { name: /Incidencia #1/i }),
    ).toBeInTheDocument();
  });

  it('renders an error when fetch fails', async () => {
    mO.fetchIncidencia.mockRejectedValueOnce(new Error('missing'));
    render(<IncidenciaDetailPage />);
    expect(await screen.findByText('missing')).toBeInTheDocument();
  });

  it('shows the assign selector for a coordinador on pendiente', async () => {
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    // Selector for técnicos is present.
    expect(
      screen.getByRole('option', { name: /Seleccionar técnico/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /^Asignar$/i }),
    ).toBeInTheDocument();
  });

  it('assigns responsable when coordinador clicks Asignar', async () => {
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    // The técnico selector is the first combobox in the DOM.
    const combos = screen.getAllByRole('combobox');
    await usr.selectOptions(combos[0], '10');
    await usr.click(screen.getByRole('button', { name: /^Asignar$/i }));
    await waitFor(() =>
      expect(mO.updateIncidencia).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ responsable_id: 10 }),
      ),
    );
  });

  it('shows the "Verificar y cerrar" button when estado=resuelto', async () => {
    mO.fetchIncidencia.mockResolvedValueOnce(makeInc({ estado: 'resuelto' }));
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    const cerrar = await screen.findByRole('button', {
      name: /Verificar y cerrar/i,
    });
    await usr.click(cerrar);
    await waitFor(() =>
      expect(mO.updateIncidencia).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ estado: 'finalizado' }),
      ),
    );
  });

  it('cancels an incidencia after confirm=true', async () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    await usr.click(screen.getByRole('button', { name: /^Cancelar$/i }));
    await waitFor(() =>
      expect(mO.updateIncidencia).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ estado: 'cancelado' }),
      ),
    );
  });

  it('shows the mantenimiento form for a técnico', async () => {
    authRol = 'tecnico';
    mO.fetchIncidencia.mockResolvedValueOnce(
      makeInc({ estado: 'en_ejecucion', responsable_id: 10 }),
    );
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    expect(
      screen.getByRole('button', { name: /Guardar mantenimiento/i }),
    ).toBeInTheDocument();
  });

  it('submits mantenimiento when técnico fills form', async () => {
    authRol = 'tecnico';
    mO.fetchIncidencia.mockResolvedValueOnce(
      makeInc({ estado: 'en_ejecucion', responsable_id: 10 }),
    );
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('button', { name: /Guardar mantenimiento/i });
    const textareas = document.querySelectorAll('textarea');
    await usr.type(textareas[0] as HTMLTextAreaElement, 'diagnostico');
    await usr.type(textareas[1] as HTMLTextAreaElement, 'acciones');
    await usr.type(textareas[2] as HTMLTextAreaElement, 'conclusion');
    await act(async () => {
      await usr.click(
        screen.getByRole('button', { name: /Guardar mantenimiento/i }),
      );
    });
    await waitFor(() => expect(mO.submitMantenimiento).toHaveBeenCalled());
  });

  it('renders existing mantenimiento in view mode', async () => {
    mO.fetchIncidencia.mockResolvedValueOnce(
      makeInc({
        estado: 'resuelto',
        responsable_id: 10,
        mantenimiento_correctivo: {
          id: 100,
          incidencia_id: 1,
          diagnostico: 'Sensor sucio',
          acciones_realizadas: 'Se cambio',
          conclusion: 'OK',
          fecha_ejecucion: '2026-01-01T00:00:00Z',
          repuestos: [
            { id: 1, nombre: 'Filtro', categoria: 'Filtros y Consumibles' },
          ],
          adjuntos: [
            { id: 1, filename: 'foto.jpg', file_url: 'https://x/x.jpg' },
          ],
          created_at: '2026-01-01',
        },
      }),
    );
    render(<IncidenciaDetailPage />);
    expect(await screen.findByText('Sensor sucio')).toBeInTheDocument();
    expect(screen.getByText('foto.jpg')).toBeInTheDocument();
  });
});
