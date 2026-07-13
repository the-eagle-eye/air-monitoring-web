import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LecturasPage from './page';
import * as lecturasApi from '@/lib/api/lecturas';
import type { Equipo } from '@/types/lectura';

jest.mock('@/lib/api/lecturas');
const mL = lecturasApi as jest.Mocked<typeof lecturasApi>;

const equipos: Equipo[] = [
  { id: 1, device_id: 'T-1', nombre: 'Est-A' } as Equipo,
  { id: 2, device_id: 'T-2', nombre: 'Est-B' } as Equipo,
];

beforeEach(() => {
  jest.clearAllMocks();
  mL.fetchEquipos.mockResolvedValue(equipos);
  mL.fetchLecturas.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 50,
  });
});

describe('LecturasPage', () => {
  it('renders the heading and equipo selector', async () => {
    render(<LecturasPage />);
    expect(
      screen.getByRole('heading', { name: /Lecturas IoT/i }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole('option', { name: /T-1/ }),
    ).toBeInTheDocument();
  });

  it('fetches lecturas when the selected equipo changes', async () => {
    const usr = userEvent.setup();
    render(<LecturasPage />);
    await waitFor(() =>
      expect(mL.fetchLecturas).toHaveBeenCalledWith('T-1', 1, 50),
    );
    await usr.selectOptions(screen.getByRole('combobox'), 'T-2');
    await waitFor(() =>
      expect(mL.fetchLecturas).toHaveBeenCalledWith('T-2', 1, 50),
    );
  });

  it('surfaces an error banner if fetchEquipos fails', async () => {
    mL.fetchEquipos.mockRejectedValueOnce(new Error('offline'));
    render(<LecturasPage />);
    expect(await screen.findByText('offline')).toBeInTheDocument();
  });
});
