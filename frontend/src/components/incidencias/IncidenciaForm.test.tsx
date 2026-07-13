import {
  render,
  screen,
  waitFor,
  act,
  fireEvent,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import IncidenciaForm from './IncidenciaForm';
import * as lecturasApi from '@/lib/api/lecturas';
import * as opsApi from '@/lib/api/ops';
import type { Equipo } from '@/types/lectura';
import type { Usuario } from '@/types/ops';

jest.mock('@/lib/api/lecturas');
jest.mock('@/lib/api/ops');
const mL = lecturasApi as jest.Mocked<typeof lecturasApi>;
const mO = opsApi as jest.Mocked<typeof opsApi>;

const equipos: Equipo[] = [
  { id: 1, device_id: 'T-1', nombre: 'Est-A' } as Equipo,
  { id: 2, device_id: 'T-2', nombre: null } as Equipo,
];

const usuarios: Usuario[] = [
  {
    id: 10,
    email: 'a@x.com',
    nombre: 'Ana',
    apellido: 'P',
    rol: 'tecnico',
    estado: 'activo',
  },
  {
    id: 11,
    email: 'b@x.com',
    nombre: 'Bob',
    apellido: 'Q',
    rol: 'coordinador',
    estado: 'activo',
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  mL.fetchEquipos.mockResolvedValue(equipos);
  mO.fetchUsuarios.mockResolvedValue(usuarios);
});

describe('IncidenciaForm', () => {
  it('loads equipos + usuarios and auto-selects the first device', async () => {
    render(<IncidenciaForm onSubmit={jest.fn()} onCancel={jest.fn()} />);
    await waitFor(() => screen.getByRole('option', { name: /T-1 — Est-A/ }));
    expect(
      screen.getByRole('option', { name: /T-2 — Sin nombre/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: /Ana P \(tecnico\)/ }),
    ).toBeInTheDocument();
  });

  it('shows an error when submitting without a responsable', async () => {
    const onSubmit = jest.fn();
    render(<IncidenciaForm onSubmit={onSubmit} onCancel={jest.fn()} />);
    await waitFor(() => screen.getByRole('option', { name: /T-1/ }));
    // The responsable select is HTML-required; submit the form directly to
    // bypass jsdom's default form validation and exercise the JS guard.
    const form = screen
      .getByRole('button', { name: 'Crear Incidencia' })
      .closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });
    expect(
      await screen.findByText('Responsable es obligatorio'),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits the assembled payload with numeric responsable_id', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const usr = userEvent.setup();
    render(<IncidenciaForm onSubmit={onSubmit} onCancel={jest.fn()} />);
    await waitFor(() => screen.getByRole('option', { name: /Ana P/ }));

    // Change device to T-2, tipo to calibracion, priority to alta, pick Ana, add description.
    const selects = screen.getAllByRole('combobox');
    // Order in DOM: equipo, tipo, prioridad, responsable
    await usr.selectOptions(selects[0], 'T-2');
    await usr.selectOptions(selects[1], 'calibracion');
    await usr.selectOptions(selects[2], 'alta');
    await usr.selectOptions(selects[3], '10');
    await usr.type(screen.getByRole('textbox'), 'sensor sucio');

    await usr.click(screen.getByRole('button', { name: 'Crear Incidencia' }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        device_id: 'T-2',
        tipo: 'calibracion',
        prioridad: 'alta',
        descripcion: 'sensor sucio',
        responsable_id: 10,
      }),
    );
  });

  it('omits descripcion when the textarea is empty', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const usr = userEvent.setup();
    render(<IncidenciaForm onSubmit={onSubmit} onCancel={jest.fn()} />);
    await waitFor(() => screen.getByRole('option', { name: /Ana P/ }));
    const selects = screen.getAllByRole('combobox');
    await usr.selectOptions(selects[3], '11');
    await usr.click(screen.getByRole('button', { name: 'Crear Incidencia' }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ descripcion: undefined, responsable_id: 11 }),
      ),
    );
  });

  it('surfaces the error message when onSubmit rejects', async () => {
    const onSubmit = jest.fn().mockRejectedValue(new Error('boom'));
    const usr = userEvent.setup();
    render(<IncidenciaForm onSubmit={onSubmit} onCancel={jest.fn()} />);
    await waitFor(() => screen.getByRole('option', { name: /Ana P/ }));
    const selects = screen.getAllByRole('combobox');
    await usr.selectOptions(selects[3], '11');
    await act(async () => {
      await usr.click(screen.getByRole('button', { name: 'Crear Incidencia' }));
    });
    expect(await screen.findByText('boom')).toBeInTheDocument();
  });

  it('calls onCancel', async () => {
    const onCancel = jest.fn();
    const usr = userEvent.setup();
    render(<IncidenciaForm onSubmit={jest.fn()} onCancel={onCancel} />);
    await waitFor(() => screen.getByRole('option', { name: /Ana P/ }));
    await usr.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('tolerates failures loading equipos / usuarios', async () => {
    mL.fetchEquipos.mockRejectedValueOnce(new Error('offline'));
    mO.fetchUsuarios.mockRejectedValueOnce(new Error('offline'));
    render(<IncidenciaForm onSubmit={jest.fn()} onCancel={jest.fn()} />);
    // Form still renders with empty selects.
    expect(
      await screen.findByRole('button', { name: 'Crear Incidencia' }),
    ).toBeInTheDocument();
  });
});
