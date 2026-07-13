import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReportesPage from './page';
import * as opsApi from '@/lib/api/ops';

let authRol = 'administrador';
jest.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'a@x.com', nombre: 'A', apellido: 'B', rol: authRol },
  }),
}));

jest.mock('@/lib/api/ops');
const mO = opsApi as jest.Mocked<typeof opsApi>;

beforeEach(() => {
  jest.clearAllMocks();
  authRol = 'administrador';
  mO.fetchReportePreview.mockResolvedValue({ items: [], total: 0 });
  mO.downloadReporte.mockResolvedValue(undefined);
});

describe('ReportesPage', () => {
  it('shows a permission error for tecnico', () => {
    authRol = 'tecnico';
    render(<ReportesPage />);
    expect(
      screen.getByText(/No tiene permisos para acceder/i),
    ).toBeInTheDocument();
  });

  it('renders the filters + heading for admin', () => {
    render(<ReportesPage />);
    expect(
      screen.getByRole('heading', { name: /Reportes de Auditoria/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Buscar/i })).toBeInTheDocument();
  });

  it('runs the search on click', async () => {
    const usr = userEvent.setup();
    render(<ReportesPage />);
    await usr.click(screen.getByRole('button', { name: /Buscar/i }));
    await waitFor(() => expect(mO.fetchReportePreview).toHaveBeenCalled());
  });

  it('exports CSV after searching', async () => {
    const usr = userEvent.setup();
    render(<ReportesPage />);
    await usr.click(screen.getByRole('button', { name: /Buscar/i }));
    await screen.findByRole('button', { name: /Exportar CSV/i });
    await usr.click(screen.getByRole('button', { name: /Exportar CSV/i }));
    await waitFor(() =>
      expect(mO.downloadReporte).toHaveBeenCalledWith(
        'csv',
        expect.any(Object),
      ),
    );
  });

  it('surfaces error on search failure', async () => {
    mO.fetchReportePreview.mockRejectedValueOnce(new Error('boom'));
    const usr = userEvent.setup();
    render(<ReportesPage />);
    await usr.click(screen.getByRole('button', { name: /Buscar/i }));
    expect(await screen.findByText('boom')).toBeInTheDocument();
  });

  it('renders result rows with correctiva and calibracion diagnostico', async () => {
    mO.fetchReportePreview.mockResolvedValueOnce({
      items: [
        {
          id_incidencia: 1,
          device_id: 'T-1',
          equipo_nombre: 'A',
          ubicacion: 'Lima',
          modelo: 'M',
          marca: 'X',
          tipo: 'correctiva',
          estado: 'finalizado',
          prioridad: 'alta',
          descripcion: 'x',
          responsable: 'Ana',
          fecha_creacion: '2026-01-01T00:00:00Z',
          fecha_actualizacion: '',
          diagnostico: 'Sensor sucio',
          acciones_realizadas: '',
          conclusion: '',
          fecha_ejecucion: '',
          repuestos_usados: '',
          fecha_calibracion: '',
          proveedor: '',
          certificado_url: '',
          nota_calibracion: '',
        },
        {
          id_incidencia: 2,
          device_id: 'T-2',
          equipo_nombre: 'B',
          ubicacion: 'Lima',
          modelo: 'M',
          marca: 'X',
          tipo: 'calibracion',
          estado: 'finalizado',
          prioridad: 'baja',
          descripcion: '',
          responsable: 'Bob',
          fecha_creacion: '2026-01-02T00:00:00Z',
          fecha_actualizacion: '',
          diagnostico: '',
          acciones_realizadas: '',
          conclusion: '',
          fecha_ejecucion: '',
          repuestos_usados: '',
          fecha_calibracion: '2026-01-05',
          proveedor: 'AcmeCal',
          certificado_url: '',
          nota_calibracion: 'todo ok',
        },
      ],
      total: 2,
    });
    const usr = userEvent.setup();
    render(<ReportesPage />);
    await usr.click(screen.getByRole('button', { name: /Buscar/i }));
    expect(await screen.findByText('T-1')).toBeInTheDocument();
    expect(screen.getByText(/Sensor sucio/i)).toBeInTheDocument();
    expect(screen.getByText(/todo ok/i)).toBeInTheDocument();
  });

  it('exports PDF after searching', async () => {
    const usr = userEvent.setup();
    render(<ReportesPage />);
    await usr.click(screen.getByRole('button', { name: /Buscar/i }));
    await screen.findByRole('button', { name: /Exportar PDF/i });
    await usr.click(screen.getByRole('button', { name: /Exportar PDF/i }));
    await waitFor(() =>
      expect(mO.downloadReporte).toHaveBeenCalledWith(
        'pdf',
        expect.any(Object),
      ),
    );
  });
});
