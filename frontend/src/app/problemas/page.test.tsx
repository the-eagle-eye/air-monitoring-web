import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProblemasPage from './page';
import * as opsApi from '@/lib/api/ops';
import type { Problema } from '@/types/ops';

jest.mock('@/lib/api/ops');
const mO = opsApi as jest.Mocked<typeof opsApi>;

const problemas: Problema[] = [
  {
    id: 1,
    device_id: 'T-1',
    titulo: 'Sensor SO2 fallando',
    descripcion: 'x',
    estado: 'abierto',
    causa_raiz: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  mO.fetchProblemas.mockResolvedValue({ items: problemas, total: 1 });
});

describe('ProblemasPage', () => {
  it('renders the list', async () => {
    render(<ProblemasPage />);
    expect(await screen.findByText('Sensor SO2 fallando')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /Gestion de Problemas/i }),
    ).toBeInTheDocument();
  });

  it('opens the create form and submits', async () => {
    mO.createProblema.mockResolvedValueOnce({ id: 2 } as never);
    const usr = userEvent.setup();
    render(<ProblemasPage />);
    await screen.findByText('Sensor SO2 fallando');
    await usr.click(screen.getByRole('button', { name: /Nuevo Problema/i }));
    const titulo = screen.getByPlaceholderText(/Fallas recurrentes/i);
    await usr.type(titulo, 'Nuevo caso');
    await usr.click(screen.getByRole('button', { name: /Crear Problema/i }));
    await waitFor(() =>
      expect(mO.createProblema).toHaveBeenCalledWith(
        expect.objectContaining({ titulo: 'Nuevo caso' }),
      ),
    );
  });

  it('shows an error on fetch failure', async () => {
    mO.fetchProblemas.mockRejectedValueOnce(new Error('offline'));
    render(<ProblemasPage />);
    expect(await screen.findByText('offline')).toBeInTheDocument();
  });
});
