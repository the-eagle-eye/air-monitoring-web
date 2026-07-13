import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginPage from './page';

const login = jest.fn();

jest.mock('@/lib/auth', () => ({
  useAuth: () => ({ login }),
}));

beforeEach(() => {
  jest.clearAllMocks();
});

describe('LoginPage', () => {
  it('renders the form with email + password inputs and a submit button', () => {
    render(<LoginPage />);
    expect(
      screen.getByRole('heading', { name: /Iniciar Sesion/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('usuario@oefa.gob.pe'),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText('********')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Ingresar/i }),
    ).toBeInTheDocument();
  });

  it('submits credentials by calling login()', async () => {
    login.mockResolvedValueOnce(undefined);
    const usr = userEvent.setup();
    render(<LoginPage />);
    await usr.type(
      screen.getByPlaceholderText('usuario@oefa.gob.pe'),
      'a@b.com',
    );
    await usr.type(screen.getByPlaceholderText('********'), 'secret');
    await usr.click(screen.getByRole('button', { name: /Ingresar/i }));
    await waitFor(() =>
      expect(login).toHaveBeenCalledWith('a@b.com', 'secret'),
    );
  });

  it('surfaces the error message when login rejects', async () => {
    login.mockRejectedValueOnce(new Error('credenciales invalidas'));
    const usr = userEvent.setup();
    render(<LoginPage />);
    await usr.type(
      screen.getByPlaceholderText('usuario@oefa.gob.pe'),
      'a@b.com',
    );
    await usr.type(screen.getByPlaceholderText('********'), 'bad');
    await act(async () => {
      await usr.click(screen.getByRole('button', { name: /Ingresar/i }));
    });
    expect(
      await screen.findByText('credenciales invalidas'),
    ).toBeInTheDocument();
  });
});
