import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EquiposReincidentes from './EquiposReincidentes';
import * as opsApi from '@/lib/api/ops';

jest.mock('@/lib/api/ops');
const mocked = opsApi as jest.Mocked<typeof opsApi>;

beforeEach(() => {
  jest.clearAllMocks();
});

function stubResumen(abiertos = 0) {
  mocked.fetchProblemasResumen.mockResolvedValue({
    por_estado: {},
    abiertos,
    total: abiertos,
  });
}

describe('EquiposReincidentes', () => {
  it('renders nothing while loading', () => {
    mocked.fetchReincidentes.mockReturnValue(new Promise(() => {}));
    stubResumen();
    const { container } = render(<EquiposReincidentes canCrear />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the empty state after load if there are no reincidentes and no open problems', async () => {
    mocked.fetchReincidentes.mockResolvedValueOnce({
      dias: 90,
      min_correctivas: 3,
      items: [],
    });
    stubResumen(0);
    render(<EquiposReincidentes canCrear />);
    await waitFor(() =>
      expect(
        screen.getByText(/Sin equipos con correctivas recurrentes/),
      ).toBeInTheDocument(),
    );
    // With no open problems, the link shows the fallback text.
    expect(screen.getByText(/Ver todos →/)).toBeInTheDocument();
  });

  it('renders the pluralized abiertos link when there are open problems', async () => {
    mocked.fetchReincidentes.mockResolvedValueOnce({
      dias: 90,
      min_correctivas: 3,
      items: [],
    });
    stubResumen(3);
    render(<EquiposReincidentes canCrear />);
    await waitFor(() =>
      expect(screen.getByText(/3 abiertos →/)).toBeInTheDocument(),
    );
  });

  it('lists reincidentes and shows the "Crear problema" action when canCrear', async () => {
    mocked.fetchReincidentes.mockResolvedValueOnce({
      dias: 90,
      min_correctivas: 3,
      items: [
        {
          device_id: 'T-1',
          correctivas: 4,
          desde: '2026-04-01',
          incidencia_ids: [10, 11],
        },
      ],
    });
    stubResumen(0);
    render(<EquiposReincidentes canCrear />);
    await waitFor(() => expect(screen.getByText('T-1')).toBeInTheDocument());
    expect(screen.getByText('4 correctivas / 90d')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Crear problema' }),
    ).toBeInTheDocument();
  });

  it('hides the "Crear problema" button when canCrear=false', async () => {
    mocked.fetchReincidentes.mockResolvedValueOnce({
      dias: 90,
      min_correctivas: 3,
      items: [
        {
          device_id: 'T-1',
          correctivas: 4,
          desde: '2026-04-01',
          incidencia_ids: [10],
        },
      ],
    });
    stubResumen(0);
    render(<EquiposReincidentes canCrear={false} />);
    await waitFor(() => expect(screen.getByText('T-1')).toBeInTheDocument());
    expect(
      screen.queryByRole('button', { name: /Crear problema/ }),
    ).not.toBeInTheDocument();
  });

  it('creates a Problema, links each incidencia, and hides the row on success', async () => {
    mocked.fetchReincidentes.mockResolvedValueOnce({
      dias: 90,
      min_correctivas: 3,
      items: [
        {
          device_id: 'T-1',
          correctivas: 4,
          desde: '2026-04-01',
          incidencia_ids: [10, 11],
        },
      ],
    });
    stubResumen(0);
    mocked.createProblema.mockResolvedValueOnce({
      id: 77,
    } as never);
    mocked.linkIncidenciaProblema.mockResolvedValue({} as never);

    const onProblemaCreado = jest.fn();
    const user = userEvent.setup();
    render(
      <EquiposReincidentes canCrear onProblemaCreado={onProblemaCreado} />,
    );
    await waitFor(() => screen.getByText('T-1'));

    await user.click(screen.getByRole('button', { name: 'Crear problema' }));

    await waitFor(() =>
      expect(screen.queryByText('T-1')).not.toBeInTheDocument(),
    );
    expect(mocked.createProblema).toHaveBeenCalledWith(
      expect.objectContaining({ device_id: 'T-1' }),
    );
    expect(mocked.linkIncidenciaProblema).toHaveBeenCalledWith(10, 77);
    expect(mocked.linkIncidenciaProblema).toHaveBeenCalledWith(11, 77);
    expect(onProblemaCreado).toHaveBeenCalled();
    expect(
      screen.getByText(/Problema #77 creado para T-1/),
    ).toBeInTheDocument();
  });

  it('shows an error message and reloads if createProblema fails', async () => {
    mocked.fetchReincidentes.mockResolvedValue({
      dias: 90,
      min_correctivas: 3,
      items: [
        {
          device_id: 'T-1',
          correctivas: 3,
          desde: '2026-04-01',
          incidencia_ids: [10],
        },
      ],
    });
    stubResumen(0);
    mocked.createProblema.mockRejectedValueOnce(new Error('boom'));

    const user = userEvent.setup();
    render(<EquiposReincidentes canCrear />);
    await waitFor(() => screen.getByText('T-1'));

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Crear problema' }));
    });

    await waitFor(() =>
      expect(
        screen.getByText('No se pudo crear el problema; reintenta'),
      ).toBeInTheDocument(),
    );
    // Reload was triggered → fetchReincidentes called at least twice.
    expect(mocked.fetchReincidentes.mock.calls.length).toBeGreaterThanOrEqual(
      2,
    );
  });

  it('swallows fetch errors gracefully (keeps loading→resolved with empty items)', async () => {
    mocked.fetchReincidentes.mockRejectedValueOnce(new Error('offline'));
    mocked.fetchProblemasResumen.mockRejectedValueOnce(new Error('offline'));
    render(<EquiposReincidentes canCrear />);
    await waitFor(() =>
      expect(
        screen.getByText(/Sin equipos con correctivas recurrentes/),
      ).toBeInTheDocument(),
    );
  });
});
