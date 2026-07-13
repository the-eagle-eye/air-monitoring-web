import { render, screen } from '@testing-library/react';
import EquiposAtencion from './EquiposAtencion';
import type { HealthDeviceState } from '@/types/healthMonitor';
import type { Incidencia } from '@/types/ops';

function state(
  overrides: Partial<HealthDeviceState> & {
    device_id: string;
    health_state: HealthDeviceState['health_state'];
  },
): HealthDeviceState {
  return {
    last_recon_error: null,
    theta: null,
    hours_since_prev: null,
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('EquiposAtencion', () => {
  it('renders the empty state when there are no anomalies or open incidents', () => {
    render(
      <EquiposAtencion
        states={{ 'T-1': state({ device_id: 'T-1', health_state: 'SANO' }) }}
      />,
    );
    expect(
      screen.getByText(/Ningún equipo con anomalía ni incidencia abierta/),
    ).toBeInTheDocument();
  });

  it('lists equipos with anomalous health states', () => {
    render(
      <EquiposAtencion
        states={{
          'T-CRIT': state({ device_id: 'T-CRIT', health_state: 'CRITICO' }),
          'T-OBS': state({ device_id: 'T-OBS', health_state: 'OBSERVADO' }),
          'T-OK': state({ device_id: 'T-OK', health_state: 'SANO' }),
        }}
      />,
    );
    expect(screen.getByText('T-CRIT')).toBeInTheDocument();
    expect(screen.getByText('T-OBS')).toBeInTheDocument();
    expect(screen.queryByText('T-OK')).not.toBeInTheDocument();
  });

  it('sorts anomalies by severity (CRITICO first)', () => {
    render(
      <EquiposAtencion
        states={{
          'T-OBS': state({ device_id: 'T-OBS', health_state: 'OBSERVADO' }),
          'T-CRIT': state({ device_id: 'T-CRIT', health_state: 'CRITICO' }),
          'T-RSK': state({ device_id: 'T-RSK', health_state: 'EN_RIESGO' }),
        }}
      />,
    );
    const rows = screen
      .getAllByRole('link')
      .filter((a) => a.getAttribute('href')?.startsWith('/equipos/'));
    expect(rows[0].getAttribute('href')).toBe('/equipos/T-CRIT');
    expect(rows[1].getAttribute('href')).toBe('/equipos/T-RSK');
    expect(rows[2].getAttribute('href')).toBe('/equipos/T-OBS');
  });

  it('shows "En seguimiento" for a SANO equipo with an open incidencia', () => {
    render(
      <EquiposAtencion
        states={{ 'T-1': state({ device_id: 'T-1', health_state: 'SANO' }) }}
        openIncidencias={[{ id: 1, device_id: 'T-1' } as Incidencia]}
      />,
    );
    expect(screen.getByText('En seguimiento')).toBeInTheDocument();
    expect(screen.getByText('incidencia abierta')).toBeInTheDocument();
  });

  it('adds an equipo missing from states if it has an open incidencia', () => {
    render(
      <EquiposAtencion
        states={{}}
        openIncidencias={[{ id: 5, device_id: 'T-GHOST' } as Incidencia]}
      />,
    );
    expect(screen.getByText('T-GHOST')).toBeInTheDocument();
    expect(screen.getByText('En seguimiento')).toBeInTheDocument();
  });

  it('links to /incidencias at the bottom', () => {
    render(<EquiposAtencion states={{}} />);
    const link = screen
      .getAllByRole('link')
      .find((a) => a.getAttribute('href') === '/incidencias');
    expect(link).toBeDefined();
  });
});
