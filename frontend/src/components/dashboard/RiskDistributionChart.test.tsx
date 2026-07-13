import { render, screen, waitFor } from '@testing-library/react';
import RiskDistributionChart from './RiskDistributionChart';
import type { RiskDistribution } from '@/types/dashboard';

// Simulate next/dynamic so the loader is invoked, resolves in a microtask,
// and the wrapped component re-renders once the module is ready. This lets
// jsdom actually run the inner CustomLabel / CustomTooltip / RiskPieChart
// closures instead of stopping at the loading placeholder.
jest.mock('next/dynamic', () => {
  const React = jest.requireActual('react');
  return (loader: () => Promise<unknown>) => {
    function Wrapped(props: Record<string, unknown>) {
      const [Comp, setComp] = React.useState<unknown>(null);
      React.useEffect(() => {
        let mounted = true;
        loader().then((v) => {
          if (mounted) setComp(() => v);
        });
        return () => {
          mounted = false;
        };
      }, []);
      if (!Comp) return <div data-testid="chart-loading" />;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const C = Comp as any;
      return <C {...props} />;
    }
    Wrapped.displayName = 'DynamicMock';
    return Wrapped;
  };
});

// The recharts mock invokes the function props (label, Tooltip content,
// Legend formatter) so the inner closures inside the chart are actually
// exercised by the test.
jest.mock('recharts', () => {
  const React = jest.requireActual('react');
  const passthrough = (name: string) => {
    const Component = ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': name }, children);
    Component.displayName = name;
    return Component;
  };
  function Pie({
    label,
    children,
  }: {
    label?: unknown;
    labelLine?: unknown;
    children?: React.ReactNode;
  }) {
    let labelNode: React.ReactNode = null;
    if (typeof label === 'function') {
      // Call the CustomLabel function with realistic label props so its
      // branches (text anchor "start" and "end") get exercised.
      const startEl = (
        label as (p: Record<string, unknown>) => React.ReactNode
      )({
        cx: 100,
        cy: 100,
        midAngle: 30,
        outerRadius: 100,
        name: 'Sano',
        percent: 0.5,
      });
      const endEl = (label as (p: Record<string, unknown>) => React.ReactNode)({
        cx: 100,
        cy: 100,
        midAngle: 150,
        outerRadius: 100,
        name: 'Crítico',
        percent: 0.25,
      });
      // A default-props call to cover the ?? fallbacks.
      const fallbackEl = (
        label as (p: Record<string, unknown>) => React.ReactNode
      )({});
      labelNode = (
        <>
          {startEl}
          {endEl}
          {fallbackEl}
        </>
      );
    }
    return React.createElement(
      'div',
      { 'data-testid': 'Pie' },
      labelNode,
      children,
    );
  }
  function Tooltip({ content }: { content?: React.ReactNode }) {
    if (React.isValidElement(content)) {
      const T = content.type as React.ComponentType<Record<string, unknown>>;
      const active = React.createElement(T, {
        active: true,
        payload: [
          { name: 'Sano', value: 3, payload: { color: '#22c55e', value: 3 } },
          {
            name: 'Crítico',
            value: 2,
            payload: { color: '#ef4444', value: 2 },
          },
        ],
      });
      const singular = React.createElement(T, {
        active: true,
        payload: [
          { name: 'Sano', value: 1, payload: { color: '#22c55e', value: 1 } },
        ],
      });
      const inactive = React.createElement(T, {
        active: false,
        payload: [],
      });
      const emptyPayload = React.createElement(T, {
        active: true,
        payload: [],
      });
      // Payload where the sum is 0 — exercises the `|| 1` denominator fallback.
      const zeroSum = React.createElement(T, {
        active: true,
        payload: [
          { name: 'Sano', value: 0, payload: { color: '#22c55e', value: 0 } },
        ],
      });
      return React.createElement(
        'div',
        { 'data-testid': 'Tooltip' },
        active,
        singular,
        inactive,
        emptyPayload,
        zeroSum,
      );
    }
    return React.createElement('div', { 'data-testid': 'Tooltip' });
  }
  function Legend({ formatter }: { formatter?: unknown }) {
    let node: React.ReactNode = null;
    if (typeof formatter === 'function') {
      const known = (formatter as (v: string) => React.ReactNode)('Sano');
      const unknown = (formatter as (v: string) => React.ReactNode)(
        'DesconocidoLegendItem',
      );
      node = (
        <>
          {known}
          {unknown}
        </>
      );
    }
    return React.createElement('div', { 'data-testid': 'Legend' }, node);
  }
  return {
    PieChart: passthrough('PieChart'),
    Pie,
    Cell: passthrough('Cell'),
    Tooltip,
    Legend,
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

  it('renders the pie chart, custom label, tooltip and legend when data is present', async () => {
    const data: RiskDistribution[] = [
      { name: 'Sano', value: 3, color: '#22c55e' },
      { name: 'Crítico', value: 2, color: '#ef4444' },
    ];
    render(<RiskDistributionChart data={data} />);
    await waitFor(() =>
      expect(screen.getByTestId('PieChart')).toBeInTheDocument(),
    );
    // CustomLabel branches (right-anchor and left-anchor).
    expect(screen.getByText(/Sano \(50%\)/)).toBeInTheDocument();
    expect(screen.getByText(/Crítico \(25%\)/)).toBeInTheDocument();
    // CustomTooltip: plural "equipos" and singular "equipo".
    expect(screen.getByText(/3 equipos/)).toBeInTheDocument();
    expect(screen.getByText(/1 equipo /)).toBeInTheDocument();
    // Legend formatter uses the count from the matched data item, and
    // falls back to 0 when the entry name is not in the data set.
    expect(screen.getByText(/Sano \(3\)/)).toBeInTheDocument();
    expect(screen.getByText(/DesconocidoLegendItem \(0\)/)).toBeInTheDocument();
  });

  it('uses paddingAngle=0 branch when a single slice is visible', async () => {
    const data: RiskDistribution[] = [
      { name: 'Sano', value: 4, color: '#22c55e' },
      { name: 'Crítico', value: 0, color: '#ef4444' },
    ];
    render(<RiskDistributionChart data={data} />);
    await waitFor(() =>
      expect(screen.getByTestId('PieChart')).toBeInTheDocument(),
    );
  });
});
