import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NuevoEquipoPage from './page';
import * as lecturasApi from '@/lib/api/lecturas';

const push = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace: jest.fn() }),
}));

jest.mock('@/lib/api/lecturas');
const mL = lecturasApi as jest.Mocked<typeof lecturasApi>;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('NuevoEquipoPage', () => {
  it('renders the EquipoForm', () => {
    render(<NuevoEquipoPage />);
    expect(
      screen.getByRole('heading', { name: /Nuevo Equipo/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Crear Equipo/i }),
    ).toBeInTheDocument();
  });

  it('calls createEquipo and navigates on submit', async () => {
    mL.createEquipo.mockResolvedValueOnce({ device_id: 'T-99' } as never);
    const usr = userEvent.setup();
    render(<NuevoEquipoPage />);
    // Fill required device_id field.
    const inputs = screen.getAllByRole('textbox');
    // First textbox in form is device_id.
    await usr.type(inputs[0], 'T-99');
    await usr.click(screen.getByRole('button', { name: /Crear Equipo/i }));
    await waitFor(() =>
      expect(mL.createEquipo).toHaveBeenCalledWith(
        expect.objectContaining({ device_id: 'T-99' }),
      ),
    );
    expect(push).toHaveBeenCalledWith('/equipos');
  });
});
