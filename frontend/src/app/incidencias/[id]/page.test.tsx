import {
  render,
  screen,
  waitFor,
  act,
  fireEvent,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import IncidenciaDetailPage from './page';
import * as opsApi from '@/lib/api/ops';
import type { Incidencia, Usuario, Repuesto } from '@/types/ops';

const routerBack = jest.fn();
jest.mock('next/navigation', () => ({
  useParams: () => ({ id: '1' }),
  useRouter: () => ({
    back: routerBack,
    push: jest.fn(),
    replace: jest.fn(),
  }),
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

  it('does not cancel when the confirm dialog is dismissed', async () => {
    jest.spyOn(window, 'confirm').mockReturnValue(false);
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    await usr.click(screen.getByRole('button', { name: /^Cancelar$/i }));
    // The API call is skipped; only the confirm() is invoked.
    expect(mO.updateIncidencia).not.toHaveBeenCalled();
  });

  it('renders low-priority incidencias with the success badge and back button', async () => {
    routerBack.mockClear();
    mO.fetchIncidencia.mockResolvedValueOnce(makeInc({ prioridad: 'baja' }));
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    expect(screen.getAllByText('Baja').length).toBeGreaterThan(0);
    await usr.click(screen.getByRole('button', { name: /^Volver$/i }));
    expect(routerBack).toHaveBeenCalled();
  });

  it('surfaces an error message when asignar fails', async () => {
    mO.updateIncidencia.mockRejectedValueOnce(new Error('backend explotó'));
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    const combos = screen.getAllByRole('combobox');
    await usr.selectOptions(combos[0], '10');
    await usr.click(screen.getByRole('button', { name: /^Asignar$/i }));
    expect(await screen.findByText('backend explotó')).toBeInTheDocument();
  });

  it('surfaces an error message when cerrar fails', async () => {
    mO.fetchIncidencia.mockResolvedValueOnce(makeInc({ estado: 'resuelto' }));
    mO.updateIncidencia.mockRejectedValueOnce(new Error('fallo cierre'));
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    const cerrar = await screen.findByRole('button', {
      name: /Verificar y cerrar/i,
    });
    await usr.click(cerrar);
    expect(await screen.findByText('fallo cierre')).toBeInTheDocument();
  });

  it('surfaces an error message when cancelar fails', async () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    mO.updateIncidencia.mockRejectedValueOnce(new Error('fallo cancelar'));
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    await usr.click(screen.getByRole('button', { name: /^Cancelar$/i }));
    expect(await screen.findByText('fallo cancelar')).toBeInTheDocument();
  });

  it('validates required fields before submitting mantenimiento', async () => {
    authRol = 'tecnico';
    mO.fetchIncidencia.mockResolvedValueOnce(
      makeInc({ estado: 'en_ejecucion', responsable_id: 10 }),
    );
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    const btn = await screen.findByRole('button', {
      name: /Guardar mantenimiento/i,
    });
    await usr.click(btn);
    expect(
      await screen.findByText(
        /Diagnóstico, Acciones y Conclusión son obligatorios/i,
      ),
    ).toBeInTheDocument();
    expect(mO.submitMantenimiento).not.toHaveBeenCalled();
  });

  it('surfaces an error message when submit mantenimiento fails', async () => {
    authRol = 'tecnico';
    mO.fetchIncidencia.mockResolvedValueOnce(
      makeInc({ estado: 'en_ejecucion', responsable_id: 10 }),
    );
    mO.submitMantenimiento.mockRejectedValueOnce(new Error('fallo submit'));
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('button', { name: /Guardar mantenimiento/i });
    const textareas = document.querySelectorAll('textarea');
    await usr.type(textareas[0] as HTMLTextAreaElement, 'd');
    await usr.type(textareas[1] as HTMLTextAreaElement, 'a');
    await usr.type(textareas[2] as HTMLTextAreaElement, 'c');
    await act(async () => {
      await usr.click(
        screen.getByRole('button', { name: /Guardar mantenimiento/i }),
      );
    });
    expect(await screen.findByText('fallo submit')).toBeInTheDocument();
  });

  it('lets a técnico toggle repuestos, add/update/remove adjuntos and closes on outside click', async () => {
    authRol = 'tecnico';
    mO.fetchIncidencia.mockResolvedValueOnce(
      makeInc({ estado: 'en_ejecucion', responsable_id: 10 }),
    );
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('button', { name: /Guardar mantenimiento/i });

    // Open the repuestos dropdown, tick a repuesto, then close it.
    const toggle = screen.getByRole('button', {
      name: /Seleccionar repuestos/i,
    });
    await usr.click(toggle);
    const checkbox = await screen.findByRole('checkbox', { name: /Filtro/i });
    await usr.click(checkbox);
    expect(
      screen.getByRole('button', { name: /1 repuesto seleccionado/i }),
    ).toBeInTheDocument();
    // Untoggle to hit the "already selected" branch of toggleRepuesto.
    await usr.click(checkbox);

    // Click outside the multi-select to close it (the mousedown listener).
    await act(async () => {
      document.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    });

    // Add an adjunto, edit both fields, then remove it.
    await usr.click(screen.getByRole('button', { name: /Agregar Adjunto/i }));
    const inputs = document.querySelectorAll('input[type="text"]');
    await usr.type(inputs[0] as HTMLInputElement, 'foto.jpg');
    await usr.type(inputs[1] as HTMLInputElement, 'https://x/foto.jpg');
    await usr.click(screen.getByRole('button', { name: /^Eliminar$/i }));
    expect(document.querySelectorAll('input[type="text"]')).toHaveLength(0);
  });

  it('shows the Ver Problema link when the incidencia has problema_id', async () => {
    mO.fetchIncidencia.mockResolvedValueOnce(
      makeInc({ estado: 'resuelto', problema_id: 42 }),
    );
    render(<IncidenciaDetailPage />);
    const link = await screen.findByRole('link', {
      name: /Ver Problema #42/i,
    });
    expect(link).toHaveAttribute('href', '/problemas/42');
  });

  it('links the incidencia to a problema when the coordinador selects one', async () => {
    mO.fetchProblemas.mockResolvedValueOnce({
      items: [
        {
          id: 42,
          titulo: 'Lámpara UV',
          descripcion: null,
          device_id: 'T-1',
          estado: 'abierto',
          causa_raiz: null,
          created_at: '2026-01-01',
          updated_at: null,
        },
      ],
      total: 1,
    });
    mO.linkIncidenciaProblema.mockResolvedValueOnce(
      makeInc({ problema_id: 42 }) as never,
    );
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    // The problema select is the last combobox — options include #42.
    const combos = screen.getAllByRole('combobox');
    const problemaSelect = combos[combos.length - 1];
    await usr.selectOptions(problemaSelect, '42');
    await waitFor(() =>
      expect(mO.linkIncidenciaProblema).toHaveBeenCalledWith(1, 42),
    );
    expect(
      await screen.findByText(/Vinculada al problema/i),
    ).toBeInTheDocument();
  });

  it('unlinks the problema and surfaces the error branch on failure', async () => {
    mO.fetchIncidencia.mockResolvedValueOnce(makeInc({ problema_id: 42 }));
    mO.linkIncidenciaProblema.mockRejectedValueOnce(
      new Error('fallo vincular'),
    );
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    await screen.findByRole('heading', { name: /Incidencia #1/i });
    const combos = screen.getAllByRole('combobox');
    const problemaSelect = combos[combos.length - 1];
    await usr.selectOptions(problemaSelect, '');
    await waitFor(() =>
      expect(mO.linkIncidenciaProblema).toHaveBeenCalledWith(1, null),
    );
    expect(await screen.findByText('fallo vincular')).toBeInTheDocument();
  });

  it('formats iso strings without a trailing Z and renders media-priority incidencias', async () => {
    mO.fetchIncidencia.mockResolvedValueOnce(
      makeInc({
        prioridad: 'media',
        fecha_asignacion: '2026-05-01T12:00:00',
      }),
    );
    render(<IncidenciaDetailPage />);
    // The heading appears once the media-priority + non-Z date paths are hit.
    expect(
      await screen.findByRole('heading', { name: /Incidencia #1/i }),
    ).toBeInTheDocument();
    // Media prioridad renders as a Badge with the capitalised label.
    expect(screen.getAllByText('Media').length).toBeGreaterThan(0);
  });

  it('refreshes the mantenimiento fields after a successful cerrar', async () => {
    // First fetch: resuelto, ready to close.
    // Second fetch (refreshIncidencia): now finalizado + mantenimiento present,
    // exercising the mantenimiento hydration branch inside refreshIncidencia.
    mO.fetchIncidencia
      .mockResolvedValueOnce(makeInc({ estado: 'resuelto' }))
      .mockResolvedValueOnce(
        makeInc({
          estado: 'finalizado',
          mantenimiento_correctivo: {
            id: 200,
            incidencia_id: 1,
            diagnostico: 'refreshed diag',
            acciones_realizadas: 'refreshed act',
            conclusion: 'refreshed conc',
            fecha_ejecucion: '2026-06-01T00:00:00Z',
            repuestos: [],
            adjuntos: [],
            created_at: '2026-06-01',
          },
        }),
      );
    const usr = userEvent.setup();
    render(<IncidenciaDetailPage />);
    const cerrar = await screen.findByRole('button', {
      name: /Verificar y cerrar/i,
    });
    await usr.click(cerrar);
    expect(await screen.findByText('refreshed diag')).toBeInTheDocument();
  });
});
