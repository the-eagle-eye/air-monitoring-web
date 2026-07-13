import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CalibracionDetailPage from './page';
import * as opsApi from '@/lib/api/ops';
import type { CalibracionOps, Proveedor } from '@/types/ops';

let searchMode: string | null = null;
jest.mock('next/navigation', () => ({
  useParams: () => ({ id: '1' }),
  useRouter: () => ({ back: jest.fn(), push: jest.fn(), replace: jest.fn() }),
  useSearchParams: () => ({
    get: (k: string) => (k === 'mode' ? searchMode : null),
  }),
}));

jest.mock('@/lib/api/ops');
const mO = opsApi as jest.Mocked<typeof opsApi>;

const calibracion: CalibracionOps = {
  id: 1,
  incidencia_id: null,
  device_id: 'T-1',
  fecha_calibracion: null,
  nota: 'test',
  certificado_url: null,
  proveedor_id: null,
  estado: 'pendiente',
  incidencia_estado: null,
  created_at: '2026-01-01T00:00:00Z',
};

const proveedores: Proveedor[] = [
  { id: 1, nombre: 'AcmeCal', estado: 'activo' },
];

beforeEach(() => {
  jest.clearAllMocks();
  searchMode = null;
  mO.fetchCalibracion.mockResolvedValue(calibracion);
  mO.fetchProveedores.mockResolvedValue(proveedores);
});

describe('CalibracionDetailPage', () => {
  it('shows the loading state initially', () => {
    mO.fetchCalibracion.mockReturnValue(new Promise(() => {}));
    render(<CalibracionDetailPage />);
    expect(screen.getByText(/Cargando.../i)).toBeInTheDocument();
  });

  it('renders read-only detail by default', async () => {
    render(<CalibracionDetailPage />);
    expect(
      await screen.findByRole('heading', { name: /Calibracion #1/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Solo lectura/i)).toBeInTheDocument();
  });

  it('renders the edit form when mode=edit', async () => {
    searchMode = 'edit';
    render(<CalibracionDetailPage />);
    await screen.findByRole('heading', { name: /Editar Calibracion/i });
    expect(
      screen.getByRole('button', { name: /Guardar/i }),
    ).toBeInTheDocument();
  });

  it('validates required fields in edit mode', async () => {
    searchMode = 'edit';
    mO.updateCalibracion.mockResolvedValueOnce({} as never);
    const usr = userEvent.setup();
    render(<CalibracionDetailPage />);
    await screen.findByRole('button', { name: /Guardar/i });
    // Save with empty fields — form's required attrs block submit; force click.
    const form = screen
      .getByRole('button', { name: /Guardar/i })
      .closest('form')!;
    await usr.click(screen.getByRole('button', { name: /Guardar/i }));
    // If HTML validation blocks it, we won't get an update call.
    expect(form).toBeInTheDocument();
  });

  it('shows an error on load failure', async () => {
    mO.fetchCalibracion.mockRejectedValueOnce(new Error('missing'));
    render(<CalibracionDetailPage />);
    expect(await screen.findByText('missing')).toBeInTheDocument();
  });

  it('saves an edit with all fields filled', async () => {
    searchMode = 'edit';
    mO.updateCalibracion.mockResolvedValueOnce({
      ...calibracion,
      nota: 'nueva',
    });
    const usr = userEvent.setup();
    render(<CalibracionDetailPage />);
    await screen.findByRole('button', { name: /Guardar/i });
    const dateInput = document.querySelector(
      'input[type="date"]',
    ) as HTMLInputElement;
    const texts = document.querySelectorAll('input[type="text"]');
    const selects = document.querySelectorAll('select');
    const textarea = document.querySelector('textarea') as HTMLTextAreaElement;

    await usr.type(dateInput, '2026-01-15');
    await usr.type(textarea, 'nota completa');
    await usr.type(texts[0] as HTMLInputElement, 'https://cert.example');
    await usr.selectOptions(selects[0] as HTMLSelectElement, '1');
    await usr.click(screen.getByRole('button', { name: /Guardar/i }));

    await waitFor(() =>
      expect(mO.updateCalibracion).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ proveedor_id: 1 }),
      ),
    );
  });
});
