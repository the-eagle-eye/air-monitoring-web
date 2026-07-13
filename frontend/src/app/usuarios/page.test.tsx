import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UsuariosPage from './page';
import * as opsApi from '@/lib/api/ops';
import type { Usuario } from '@/types/ops';

jest.mock('@/lib/api/ops');
const mO = opsApi as jest.Mocked<typeof opsApi>;

const usuarios: Usuario[] = [
  {
    id: 1,
    email: 'a@x.com',
    nombre: 'Ana',
    apellido: 'P',
    rol: 'tecnico',
    estado: 'activo',
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  mO.fetchUsuarios.mockResolvedValue(usuarios);
});

describe('UsuariosPage', () => {
  it('renders the list', async () => {
    render(<UsuariosPage />);
    expect(await screen.findByText('a@x.com')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /Usuarios/i }),
    ).toBeInTheDocument();
  });

  it('creates a new usuario via the form', async () => {
    mO.createUsuario.mockResolvedValueOnce({ id: 2 } as never);
    const usr = userEvent.setup();
    render(<UsuariosPage />);
    await screen.findByText('a@x.com');
    await usr.click(screen.getByRole('button', { name: /Nuevo Usuario/i }));

    // Form has 4 text inputs (email, nombre, apellido, password); order in DOM
    // follows the JSX: email, rol(select), nombre, apellido, password.
    const emailInput = document.querySelector(
      'input[type="email"]',
    ) as HTMLInputElement;
    const textInputs = document.querySelectorAll('input[type="text"]');
    const passwordInput = document.querySelector(
      'input[type="password"]',
    ) as HTMLInputElement;
    await usr.type(emailInput, 'new@x.com');
    await usr.type(textInputs[0] as HTMLInputElement, 'New');
    await usr.type(textInputs[1] as HTMLInputElement, 'User');
    await usr.type(passwordInput, 'secret1');
    await usr.click(screen.getByRole('button', { name: /^Crear/i }));

    await waitFor(() =>
      expect(mO.createUsuario).toHaveBeenCalledWith(
        expect.objectContaining({ email: 'new@x.com', nombre: 'New' }),
      ),
    );
  });

  it('deactivates a usuario with confirm=true', async () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    mO.deleteUsuario.mockResolvedValueOnce(undefined);
    const usr = userEvent.setup();
    render(<UsuariosPage />);
    await screen.findByText('a@x.com');
    await usr.click(screen.getByRole('button', { name: /Desactivar/i }));
    await waitFor(() => expect(mO.deleteUsuario).toHaveBeenCalledWith(1));
  });
});
