import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProveedoresPage from './page';
import * as opsApi from '@/lib/api/ops';
import type { Proveedor } from '@/types/ops';

jest.mock('@/lib/api/ops');
const mO = opsApi as jest.Mocked<typeof opsApi>;

const proveedores: Proveedor[] = [
  { id: 1, nombre: 'AcmeCal', estado: 'activo' },
];

beforeEach(() => {
  jest.clearAllMocks();
  mO.fetchProveedores.mockResolvedValue(proveedores);
});

describe('ProveedoresPage', () => {
  it('renders the list', async () => {
    render(<ProveedoresPage />);
    expect(await screen.findByText('AcmeCal')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /Proveedores/i }),
    ).toBeInTheDocument();
  });

  it('opens the create form and submits', async () => {
    mO.createProveedor.mockResolvedValueOnce({
      id: 2,
      nombre: 'X',
      estado: 'activo',
    });
    const usr = userEvent.setup();
    render(<ProveedoresPage />);
    await screen.findByText('AcmeCal');
    await usr.click(screen.getByRole('button', { name: /Nuevo Proveedor/i }));
    const inputs = screen.getAllByRole('textbox');
    await usr.type(inputs[0], 'NewProv');
    await usr.click(screen.getByRole('button', { name: /Crear/i }));
    await waitFor(() =>
      expect(mO.createProveedor).toHaveBeenCalledWith({ nombre: 'NewProv' }),
    );
  });

  it('deletes after confirm=true', async () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    mO.deleteProveedor.mockResolvedValueOnce(undefined);
    const usr = userEvent.setup();
    render(<ProveedoresPage />);
    await screen.findByText('AcmeCal');
    await usr.click(screen.getByRole('button', { name: /Eliminar/i }));
    await waitFor(() => expect(mO.deleteProveedor).toHaveBeenCalledWith(1));
  });

  it('surfaces an error banner when fetch fails', async () => {
    mO.fetchProveedores.mockRejectedValueOnce(new Error('offline'));
    render(<ProveedoresPage />);
    expect(await screen.findByText('offline')).toBeInTheDocument();
  });

  it('opens the edit form pre-populated', async () => {
    const usr = userEvent.setup();
    render(<ProveedoresPage />);
    await screen.findByText('AcmeCal');
    await act(async () => {
      await usr.click(screen.getByRole('button', { name: /Editar/i }));
    });
    expect(
      screen.getByRole('heading', { name: /Editar Proveedor/i }),
    ).toBeInTheDocument();
  });
});
