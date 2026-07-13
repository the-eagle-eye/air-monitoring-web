import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RepuestosPage from './page';
import * as opsApi from '@/lib/api/ops';
import type { Repuesto } from '@/types/ops';

jest.mock('@/lib/api/ops');
const mO = opsApi as jest.Mocked<typeof opsApi>;

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
  mO.fetchRepuestos.mockResolvedValue(repuestos);
});

describe('RepuestosPage', () => {
  it('renders the list', async () => {
    render(<RepuestosPage />);
    expect(await screen.findByText('Filtro')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /Repuestos/i }),
    ).toBeInTheDocument();
  });

  it('creates a new repuesto', async () => {
    mO.createRepuesto.mockResolvedValueOnce({
      id: 2,
      nombre: 'Nuevo',
      categoria: 'Sensores y Detectores',
      estado: 'activo',
      created_at: '2026-01-02',
    });
    const usr = userEvent.setup();
    render(<RepuestosPage />);
    await screen.findByText('Filtro');
    await usr.click(screen.getByRole('button', { name: /Nuevo Repuesto/i }));
    const inputs = screen.getAllByRole('textbox');
    await usr.type(inputs[0], 'Nuevo');
    await usr.click(screen.getByRole('button', { name: /Crear/i }));
    await waitFor(() =>
      expect(mO.createRepuesto).toHaveBeenCalledWith(
        expect.objectContaining({ nombre: 'Nuevo' }),
      ),
    );
  });

  it('opens edit and submits an update', async () => {
    mO.updateRepuesto.mockResolvedValueOnce({} as never);
    const usr = userEvent.setup();
    render(<RepuestosPage />);
    await screen.findByText('Filtro');
    await usr.click(screen.getByRole('button', { name: /Editar/i }));
    expect(
      screen.getByRole('heading', { name: /Editar Repuesto/i }),
    ).toBeInTheDocument();
    await usr.click(screen.getByRole('button', { name: /Actualizar/i }));
    await waitFor(() =>
      expect(mO.updateRepuesto).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ nombre: 'Filtro' }),
      ),
    );
  });

  it('deletes with confirm=true', async () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    mO.deleteRepuesto.mockResolvedValueOnce(undefined);
    const usr = userEvent.setup();
    render(<RepuestosPage />);
    await screen.findByText('Filtro');
    await usr.click(screen.getByRole('button', { name: /Eliminar/i }));
    await waitFor(() => expect(mO.deleteRepuesto).toHaveBeenCalledWith(1));
  });
});
