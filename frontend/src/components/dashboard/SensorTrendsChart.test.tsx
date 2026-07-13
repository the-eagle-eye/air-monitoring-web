import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SensorTrendsChart from './SensorTrendsChart';
import type { LecturaIoT } from '@/types/lectura';

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
    ResponsiveContainer: passthrough('ResponsiveContainer'),
  };
});

const OPTIONS = [{ device_id: 'T-1', label: 'Ilo-01' }];

function lect(overrides: Partial<LecturaIoT> = {}): LecturaIoT {
  return {
    id: 1,
    device_id: 1,
    equipo_device_id: 'T-1',
    timestamp_lectura: '2026-07-12T15:00:00Z',
    procesado: true,
    created_at: '2026-07-12T15:00:00Z',
    so2_ppb: 2.5,
    ...overrides,
  } as LecturaIoT;
}

describe('SensorTrendsChart', () => {
  it('renders the "select an equipo" placeholder when none is selected', () => {
    render(
      <SensorTrendsChart
        lecturas={[]}
        loading={false}
        selectedEquipo=""
        equipoOptions={OPTIONS}
        onEquipoChange={jest.fn()}
      />,
    );
    expect(
      screen.getByText('Selecciona un equipo para ver tendencias'),
    ).toBeInTheDocument();
  });

  it('renders the loading placeholder when loading', () => {
    render(
      <SensorTrendsChart
        lecturas={[]}
        loading={true}
        selectedEquipo="T-1"
        equipoOptions={OPTIONS}
        onEquipoChange={jest.fn()}
      />,
    );
    expect(screen.getByText('Cargando lecturas...')).toBeInTheDocument();
  });

  it('renders "Sin lecturas disponibles" when the list is empty', () => {
    render(
      <SensorTrendsChart
        lecturas={[]}
        loading={false}
        selectedEquipo="T-1"
        equipoOptions={OPTIONS}
        onEquipoChange={jest.fn()}
      />,
    );
    expect(screen.getByText('Sin lecturas disponibles')).toBeInTheDocument();
  });

  it('renders the chart (mocked) when data is present', () => {
    render(
      <SensorTrendsChart
        lecturas={[lect()]}
        loading={false}
        selectedEquipo="T-1"
        equipoOptions={OPTIONS}
        onEquipoChange={jest.fn()}
      />,
    );
    // No placeholder branch triggered
    expect(
      screen.queryByText('Selecciona un equipo para ver tendencias'),
    ).not.toBeInTheDocument();
    expect(screen.queryByText('Cargando lecturas...')).not.toBeInTheDocument();
    expect(
      screen.queryByText('Sin lecturas disponibles'),
    ).not.toBeInTheDocument();
  });

  it('forwards a select change to onEquipoChange', async () => {
    const onEquipoChange = jest.fn();
    const usr = userEvent.setup();
    render(
      <SensorTrendsChart
        lecturas={[]}
        loading={false}
        selectedEquipo=""
        equipoOptions={OPTIONS}
        onEquipoChange={onEquipoChange}
      />,
    );
    await usr.selectOptions(screen.getByRole('combobox'), 'T-1');
    expect(onEquipoChange).toHaveBeenCalledWith('T-1');
  });
});
