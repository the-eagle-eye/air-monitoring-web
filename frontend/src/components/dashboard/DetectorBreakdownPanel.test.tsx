import { render, screen } from '@testing-library/react';
import DetectorBreakdownPanel from './DetectorBreakdownPanel';
import type { HealthReadingPoint } from '@/types/healthMonitor';

function reading(
  overrides: Partial<HealthReadingPoint> = {},
): HealthReadingPoint {
  return {
    timestamp: '2026-07-12T00:00:00Z',
    recon_error: 0.5,
    theta: 1.0,
    health_state: 'SANO',
    and_alert: false,
    if_anomaly: false,
    severity: null,
    ...overrides,
  };
}

describe('DetectorBreakdownPanel', () => {
  it('renders nothing when reading is null', () => {
    const { container } = render(<DetectorBreakdownPanel reading={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders "Normal" for AE when recon_error < theta and IF false', () => {
    render(<DetectorBreakdownPanel reading={reading()} />);
    // Three detector rows should render "Normal" badges.
    expect(screen.getAllByText('Normal')).toHaveLength(3);
  });

  it('renders "Anomalía" for AE when recon_error > theta', () => {
    render(
      <DetectorBreakdownPanel
        reading={reading({
          recon_error: 2.0,
          theta: 1.0,
          if_anomaly: true,
          and_alert: true,
        })}
      />,
    );
    expect(screen.getAllByText('Anomalía')).toHaveLength(3);
  });

  it('renders "Sin dato" for AE when recon_error or theta is null', () => {
    render(<DetectorBreakdownPanel reading={reading({ recon_error: null })} />);
    expect(screen.getByText('Sin dato')).toBeInTheDocument();
  });

  it('renders "Sin dato" for IF when if_anomaly is null', () => {
    render(<DetectorBreakdownPanel reading={reading({ if_anomaly: null })} />);
    expect(screen.getByText('Sin dato')).toBeInTheDocument();
  });

  it('formats normal-range numbers with 4 decimals', () => {
    render(
      <DetectorBreakdownPanel
        reading={reading({ recon_error: 0.5, theta: 1.0 })}
      />,
    );
    expect(screen.getByText(/error 0\.5000/)).toBeInTheDocument();
    expect(screen.getByText(/θ 1\.0000/)).toBeInTheDocument();
  });

  it('uses scientific notation for extreme numbers', () => {
    render(
      <DetectorBreakdownPanel
        reading={reading({ recon_error: 1500, theta: 0.0001 })}
      />,
    );
    // 1500 → "1.50e+3" ; 0.0001 → "1.00e-4"
    expect(screen.getByText(/1\.50e\+3/)).toBeInTheDocument();
    expect(screen.getByText(/1\.00e-4/)).toBeInTheDocument();
  });

  it('renders "n/a" for missing recon_error/theta values', () => {
    render(
      <DetectorBreakdownPanel
        reading={reading({ recon_error: null, theta: null })}
      />,
    );
    expect(screen.getByText(/error n\/a/)).toBeInTheDocument();
  });

  it('renders the published health state at the bottom', () => {
    render(
      <DetectorBreakdownPanel reading={reading({ health_state: 'CRITICO' })} />,
    );
    expect(screen.getByText(/Crítico/)).toBeInTheDocument();
  });
});
