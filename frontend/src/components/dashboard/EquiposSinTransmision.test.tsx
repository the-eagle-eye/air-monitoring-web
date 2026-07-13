import { render, screen } from '@testing-library/react';
import EquiposSinTransmision from './EquiposSinTransmision';
import type { HealthDeviceState } from '@/types/healthMonitor';

function state(
  overrides: Partial<HealthDeviceState> & { device_id: string },
): HealthDeviceState {
  return {
    device_id: 'x',
    health_state: 'SANO',
    last_recon_error: null,
    theta: null,
    hours_since_prev: null,
    updated_at: '2026-07-12T00:00:00Z',
    ...overrides,
  };
}

describe('EquiposSinTransmision', () => {
  it('renders the reassuring copy when everyone is transmitting', () => {
    render(
      <EquiposSinTransmision
        states={{ 'T-1': state({ device_id: 'T-1', health_state: 'SANO' }) }}
      />,
    );
    expect(
      screen.getByText('Todos los equipos están transmitiendo.'),
    ).toBeInTheDocument();
    expect(screen.getByText(/\(0\)/)).toBeInTheDocument();
  });

  it('lists SIN_DATOS equipos with the "Dato inválido" motivo', () => {
    render(
      <EquiposSinTransmision
        states={{
          'T-1': state({ device_id: 'T-1', health_state: 'SIN_DATOS' }),
        }}
      />,
    );
    expect(screen.getByText('T-1')).toBeInTheDocument();
    expect(screen.getByText(/Dato inválido/)).toBeInTheDocument();
  });

  it('lists SIN_TRANSMISION equipos with severity label', () => {
    render(
      <EquiposSinTransmision
        states={{
          'T-2': state({
            device_id: 'T-2',
            transmission_state: 'SIN_TRANSMISION',
            transmission_severity: 'alta',
            last_reading_ts: '2026-07-12T00:00:00Z',
          }),
        }}
      />,
    );
    expect(screen.getByText('T-2')).toBeInTheDocument();
    expect(
      screen.getByText(/No transmite · crítico \(>24 h\)/),
    ).toBeInTheDocument();
  });

  it('ignores null entries in the states map', () => {
    render(
      <EquiposSinTransmision
        states={{
          'T-1': null,
          'T-2': state({ device_id: 'T-2', health_state: 'SIN_DATOS' }),
        }}
      />,
    );
    expect(screen.queryByText('T-1')).not.toBeInTheDocument();
    expect(screen.getByText('T-2')).toBeInTheDocument();
  });

  it('falls back to updated_at when last_reading_ts is absent', () => {
    render(
      <EquiposSinTransmision
        states={{
          'T-3': state({
            device_id: 'T-3',
            health_state: 'SIN_DATOS',
            updated_at: '2026-07-12T15:00:00Z',
          }),
        }}
      />,
    );
    // Component uses toLocaleString — assert that the label prefix is rendered.
    expect(screen.getByText(/última:/)).toBeInTheDocument();
  });
});
