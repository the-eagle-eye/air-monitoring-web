import { render, screen } from '@testing-library/react';
import EquiposEnWarmup from './EquiposEnWarmup';
import type { TrainingStateItem } from '@/types/healthMonitor';

function item(overrides: Partial<TrainingStateItem>): TrainingStateItem {
  return {
    device_id: 'CA-TA-01',
    state: 'recolectando',
    readings_valid_count: 500,
    target: 2016,
    eta_days: 5.3,
    attempts: 0,
    last_error: null,
    model_version: null,
    updated_at: '2026-07-16T00:00:00Z',
    ...overrides,
  };
}

describe('EquiposEnWarmup', () => {
  it('renders nothing when there are no items (no waste of dashboard space)', () => {
    const { container } = render(<EquiposEnWarmup items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows progress and ETA for a station in recolectando', () => {
    render(<EquiposEnWarmup items={[item({})]} />);
    expect(screen.getByText('CA-TA-01')).toBeInTheDocument();
    expect(screen.getByText('Recolectando')).toBeInTheDocument();
    expect(screen.getByText(/500 \/ 2016/)).toBeInTheDocument();
    expect(screen.getByText(/ETA/)).toBeInTheDocument();
    expect(screen.getByText(/~5\.3 d/)).toBeInTheDocument();
  });

  it('shows a spinner and no ETA when state is entrenando', () => {
    render(
      <EquiposEnWarmup
        items={[
          item({
            state: 'entrenando',
            readings_valid_count: 2016,
            eta_days: null,
          }),
        ]}
      />,
    );
    expect(screen.getByText('Entrenando')).toBeInTheDocument();
    expect(screen.getByLabelText('entrenando')).toBeInTheDocument();
    expect(screen.queryByText(/ETA/)).not.toBeInTheDocument();
  });

  it('shows last_error under a station in error state', () => {
    render(
      <EquiposEnWarmup
        items={[
          item({
            state: 'error',
            last_error: 'CR-04: recon_error mediano 0.5 > 2.0× 0.1',
            eta_days: null,
          }),
        ]}
      />,
    );
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText(/CR-04/)).toBeInTheDocument();
  });

  it('formats sub-day ETAs in hours', () => {
    render(<EquiposEnWarmup items={[item({ eta_days: 0.25 })]} />);
    expect(screen.getByText(/~6 h/)).toBeInTheDocument();
  });

  it('renders multiple items in one panel', () => {
    render(
      <EquiposEnWarmup
        items={[
          item({ device_id: 'CA-TA-01' }),
          item({ device_id: 'CA-NEW-02', state: 'nueva', eta_days: null }),
        ]}
      />,
    );
    expect(screen.getByText('CA-TA-01')).toBeInTheDocument();
    expect(screen.getByText('CA-NEW-02')).toBeInTheDocument();
    expect(screen.getByText('Registrando')).toBeInTheDocument();
    expect(screen.getByText(/\(2\)/)).toBeInTheDocument();
  });
});
