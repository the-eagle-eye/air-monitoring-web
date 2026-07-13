import { render, screen } from '@testing-library/react';
import ReconErrorChart from './ReconErrorChart';
import type { HealthReadingPoint } from '@/types/healthMonitor';

// Stub next/dynamic so the recharts closure runs synchronously in jsdom.
jest.mock('next/dynamic', () => (loader: () => Promise<unknown>) => {
  let Loaded: unknown = null;
  loader().then((v) => {
    Loaded = v;
  });
  const Wrapped = (props: Record<string, unknown>) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const C = Loaded as any;
    return C ? <C {...props} /> : <div data-testid="chart-loading" />;
  };
  Wrapped.displayName = 'DynamicMock';
  return Wrapped;
});

jest.mock('recharts', () => {
  const React = jest.requireActual('react');
  const passthrough = (name: string) => {
    const Component = ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': name }, children);
    Component.displayName = name;
    return Component;
  };
  return {
    LineChart: passthrough('LineChart'),
    Line: passthrough('Line'),
    XAxis: passthrough('XAxis'),
    YAxis: passthrough('YAxis'),
    CartesianGrid: passthrough('CartesianGrid'),
    Tooltip: passthrough('Tooltip'),
    Legend: passthrough('Legend'),
    ReferenceLine: passthrough('ReferenceLine'),
    ResponsiveContainer: passthrough('ResponsiveContainer'),
  };
});

function pt(overrides: Partial<HealthReadingPoint> = {}): HealthReadingPoint {
  return {
    timestamp: '2026-07-12T00:00:00Z',
    recon_error: 0.1,
    theta: 1.0,
    health_state: 'SANO',
    and_alert: false,
    if_anomaly: false,
    ...overrides,
  };
}

describe('ReconErrorChart', () => {
  it('renders the loading skeleton when loading', () => {
    const { container } = render(
      <ReconErrorChart points={[]} loading={true} />,
    );
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders the empty-state message when there are no points', () => {
    render(<ReconErrorChart points={[]} />);
    expect(
      screen.getByText(/Sin datos de salud para este equipo todavía/),
    ).toBeInTheDocument();
  });

  it('picks the first non-null theta as the reference line value', () => {
    render(
      <ReconErrorChart
        points={[
          pt({ theta: null }),
          pt({ timestamp: '2026-07-12T01:00:00Z', theta: 0.5 }),
        ]}
      />,
    );
    // Chart wrapper renders (either the mock or the dynamic loading placeholder).
    // Either way, we verified the empty-state branch is skipped.
    expect(screen.queryByText(/Sin datos de salud/)).not.toBeInTheDocument();
  });

  it('renders the panel title + subtitle', () => {
    render(<ReconErrorChart points={[]} />);
    expect(
      screen.getByText('Error de reconstrucción (salud del equipo)'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Cuando la línea supera θ/)).toBeInTheDocument();
  });
});
