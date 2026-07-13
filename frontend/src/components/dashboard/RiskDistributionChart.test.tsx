import { render, screen } from '@testing-library/react';
import RiskDistributionChart from './RiskDistributionChart';
import type { RiskDistribution } from '@/types/dashboard';

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
    PieChart: passthrough('PieChart'),
    Pie: passthrough('Pie'),
    Cell: passthrough('Cell'),
    Tooltip: passthrough('Tooltip'),
    Legend: passthrough('Legend'),
    ResponsiveContainer: passthrough('ResponsiveContainer'),
  };
});

describe('RiskDistributionChart', () => {
  it('renders the panel title', () => {
    render(<RiskDistributionChart data={[]} />);
    expect(screen.getByText('Distribución de Salud')).toBeInTheDocument();
  });

  it('renders the empty state when all values are 0', () => {
    const empty: RiskDistribution[] = [
      { name: 'Sano', value: 0, color: '#22c55e' },
      { name: 'Crítico', value: 0, color: '#ef4444' },
    ];
    render(<RiskDistributionChart data={empty} />);
    expect(screen.getByText('Sin datos de salud')).toBeInTheDocument();
  });

  it('skips the empty state when at least one value > 0', () => {
    const data: RiskDistribution[] = [
      { name: 'Sano', value: 2, color: '#22c55e' },
      { name: 'Crítico', value: 0, color: '#ef4444' },
    ];
    render(<RiskDistributionChart data={data} />);
    expect(screen.queryByText('Sin datos de salud')).not.toBeInTheDocument();
  });
});
