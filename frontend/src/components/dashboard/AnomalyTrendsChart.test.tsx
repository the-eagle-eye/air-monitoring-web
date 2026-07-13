import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AnomalyTrendsChart from './AnomalyTrendsChart';
import * as api from '@/lib/api/healthMonitor';

jest.mock('@/lib/api/healthMonitor');
const mocked = api as jest.Mocked<typeof api>;

// Stub the child chart so we can just verify the wiring.
jest.mock('./ReconErrorChart', () => ({
  __esModule: true,
  default: ({ points, loading }: { points: unknown[]; loading?: boolean }) => (
    <div data-testid="chart" data-loading={String(!!loading)}>
      {points.length} points
    </div>
  ),
}));

beforeEach(() => {
  jest.clearAllMocks();
});

const OPTIONS = [
  { device_id: 'T-1', label: 'Ilo-01' },
  { device_id: 'T-2', label: 'Ilo-02' },
];

describe('AnomalyTrendsChart', () => {
  it('renders the equipment options in the select', () => {
    render(
      <AnomalyTrendsChart
        selectedEquipo=""
        equipoOptions={OPTIONS}
        onEquipoChange={jest.fn()}
      />,
    );
    expect(screen.getByRole('option', { name: /Ilo-01/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Ilo-02/ })).toBeInTheDocument();
  });

  it('does not fetch when selectedEquipo is empty', () => {
    render(
      <AnomalyTrendsChart
        selectedEquipo=""
        equipoOptions={OPTIONS}
        onEquipoChange={jest.fn()}
      />,
    );
    expect(mocked.fetchHealthReadings).not.toHaveBeenCalled();
    expect(screen.getByTestId('chart')).toHaveTextContent('0 points');
  });

  it('fetches when selectedEquipo changes and forwards points to the chart', async () => {
    mocked.fetchHealthReadings.mockResolvedValueOnce({
      device_id: 'T-1',
      points: [
        {
          timestamp: '2026-07-12T00:00:00Z',
          recon_error: 0.1,
          theta: 1,
          health_state: 'SANO',
          and_alert: false,
        },
      ] as never,
    });
    render(
      <AnomalyTrendsChart
        selectedEquipo="T-1"
        equipoOptions={OPTIONS}
        onEquipoChange={jest.fn()}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId('chart')).toHaveTextContent('1 points'),
    );
    expect(mocked.fetchHealthReadings).toHaveBeenCalledWith('T-1');
  });

  it('coerces fetch errors to an empty point list', async () => {
    mocked.fetchHealthReadings.mockRejectedValueOnce(new Error('offline'));
    render(
      <AnomalyTrendsChart
        selectedEquipo="T-1"
        equipoOptions={OPTIONS}
        onEquipoChange={jest.fn()}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId('chart')).toHaveAttribute(
        'data-loading',
        'false',
      ),
    );
    expect(screen.getByTestId('chart')).toHaveTextContent('0 points');
  });

  it('bubbles a device change to onEquipoChange', async () => {
    const onEquipoChange = jest.fn();
    const usr = userEvent.setup();
    render(
      <AnomalyTrendsChart
        selectedEquipo=""
        equipoOptions={OPTIONS}
        onEquipoChange={onEquipoChange}
      />,
    );
    await usr.selectOptions(screen.getByRole('combobox'), 'T-2');
    expect(onEquipoChange).toHaveBeenCalledWith('T-2');
  });
});
