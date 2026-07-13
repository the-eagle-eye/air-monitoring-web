import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EquiposPendientes from './EquiposPendientes';
import * as lecturasApi from '@/lib/api/lecturas';
import type { Equipo } from '@/types/lectura';

jest.mock('@/lib/api/lecturas');
const mocked = lecturasApi as jest.Mocked<typeof lecturasApi>;

function eq(overrides: Partial<Equipo> = {}): Equipo {
  return {
    id: 1,
    device_id: 'T-NEW',
    nombre: null,
    tipo: null,
    ubicacion: null,
    estado: 'no_confirmado',
    serie: null,
    codigo_interno: null,
    modelo: null,
    marca: null,
    fecha_ingreso: null,
    rango_medicion: null,
    parametro_medicion: null,
    foto_equipo: null,
    datalogger_id: null,
    fecha_registro: '2026-07-12T00:00:00Z',
    fecha_actualizacion: null,
    ...overrides,
  } as Equipo;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('EquiposPendientes', () => {
  it('renders nothing while loading', () => {
    mocked.fetchEquiposPendientes.mockReturnValue(new Promise(() => {}));
    const { container } = render(<EquiposPendientes canConfirm />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when the list is empty', async () => {
    mocked.fetchEquiposPendientes.mockResolvedValueOnce([]);
    const { container } = render(<EquiposPendientes canConfirm />);
    await waitFor(() => expect(container.firstChild).toBeNull());
  });

  it('renders the panel with the pendientes count and criticidad selector', async () => {
    mocked.fetchEquiposPendientes.mockResolvedValueOnce([
      eq({ device_id: 'T-1' }),
    ]);
    render(<EquiposPendientes canConfirm />);
    await waitFor(() => screen.getByText('T-1'));
    expect(screen.getByText(/Equipos por confirmar \(1\)/)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Confirmar' }),
    ).toBeInTheDocument();
  });

  it('hides the selector + button when canConfirm is false', async () => {
    mocked.fetchEquiposPendientes.mockResolvedValueOnce([
      eq({ device_id: 'T-1' }),
    ]);
    render(<EquiposPendientes canConfirm={false} />);
    await waitFor(() => screen.getByText('T-1'));
    expect(
      screen.queryByRole('button', { name: 'Confirmar' }),
    ).not.toBeInTheDocument();
    expect(screen.getByText('Pendiente de aprobación')).toBeInTheDocument();
  });

  it('confirms with the default criticidad "media" and drops the row on success', async () => {
    mocked.fetchEquiposPendientes.mockResolvedValueOnce([
      eq({ device_id: 'T-1' }),
    ]);
    mocked.confirmarEquipo.mockResolvedValueOnce(
      eq({ device_id: 'T-1', estado: 'activo' }),
    );
    const onConfirmed = jest.fn();
    const usr = userEvent.setup();
    render(<EquiposPendientes canConfirm onConfirmed={onConfirmed} />);
    await waitFor(() => screen.getByText('T-1'));
    await usr.click(screen.getByRole('button', { name: 'Confirmar' }));
    await waitFor(() =>
      expect(mocked.confirmarEquipo).toHaveBeenCalledWith('T-1', {
        criticidad: 'media',
      }),
    );
    expect(onConfirmed).toHaveBeenCalled();
  });

  it('lets the user pick criticidad "alta" before confirming', async () => {
    mocked.fetchEquiposPendientes.mockResolvedValueOnce([
      eq({ device_id: 'T-1' }),
    ]);
    mocked.confirmarEquipo.mockResolvedValueOnce(eq({ device_id: 'T-1' }));
    const usr = userEvent.setup();
    render(<EquiposPendientes canConfirm />);
    await waitFor(() => screen.getByText('T-1'));
    await usr.selectOptions(screen.getByRole('combobox'), 'alta');
    await usr.click(screen.getByRole('button', { name: 'Confirmar' }));
    expect(mocked.confirmarEquipo).toHaveBeenCalledWith('T-1', {
      criticidad: 'alta',
    });
  });

  it('reloads the list when confirmarEquipo fails', async () => {
    mocked.fetchEquiposPendientes
      .mockResolvedValueOnce([eq({ device_id: 'T-1' })])
      .mockResolvedValueOnce([eq({ device_id: 'T-1' })]);
    mocked.confirmarEquipo.mockRejectedValueOnce(new Error('nope'));
    const usr = userEvent.setup();
    render(<EquiposPendientes canConfirm />);
    await waitFor(() => screen.getByText('T-1'));
    await act(async () => {
      await usr.click(screen.getByRole('button', { name: 'Confirmar' }));
    });
    await waitFor(() =>
      expect(
        mocked.fetchEquiposPendientes.mock.calls.length,
      ).toBeGreaterThanOrEqual(2),
    );
  });

  it('coerces a fetch error to an empty list (renders nothing)', async () => {
    mocked.fetchEquiposPendientes.mockRejectedValueOnce(new Error('offline'));
    const { container } = render(<EquiposPendientes canConfirm />);
    await waitFor(() => expect(container.firstChild).toBeNull());
  });
});
