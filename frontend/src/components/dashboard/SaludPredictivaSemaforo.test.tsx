import { render, screen } from '@testing-library/react';
import SaludPredictivaSemaforo from './SaludPredictivaSemaforo';
import type { HealthDeviceState, HealthState } from '@/types/healthMonitor';

function state(device_id: string, hs: HealthState): HealthDeviceState {
  return {
    device_id,
    health_state: hs,
    last_recon_error: null,
    theta: null,
    hours_since_prev: null,
    updated_at: '2026-07-12T00:00:00Z',
  };
}

describe('SaludPredictivaSemaforo', () => {
  it('shows the "Óptimo" label with score 100 when every equipo is SANO', () => {
    render(
      <SaludPredictivaSemaforo
        states={{ A: state('A', 'SANO'), B: state('B', 'SANO') }}
      />,
    );
    expect(screen.getByText(/Salud Predictiva: Óptimo/)).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('marks any single CRITICO as "Crítico" regardless of score', () => {
    render(
      <SaludPredictivaSemaforo
        states={{
          A: state('A', 'SANO'),
          B: state('B', 'CRITICO'),
        }}
      />,
    );
    expect(screen.getByText(/Salud Predictiva: Crítico/)).toBeInTheDocument();
  });

  it('stays "Óptimo" when average penalty keeps score ≥ 75', () => {
    // Two OBSERVADO → penalty 15 → score 85
    render(
      <SaludPredictivaSemaforo
        states={{
          A: state('A', 'OBSERVADO'),
          B: state('B', 'OBSERVADO'),
        }}
      />,
    );
    expect(screen.getByText(/Óptimo/)).toBeInTheDocument();
    expect(screen.getByText('85')).toBeInTheDocument();
  });

  it('stays "Óptimo" at the boundary score of exactly 75 (avg penalty 25)', () => {
    render(
      <SaludPredictivaSemaforo
        states={{ A: state('A', 'EN_RIESGO'), B: state('B', 'EN_RIESGO') }}
      />,
    );
    expect(screen.getByText(/Óptimo/)).toBeInTheDocument();
    expect(screen.getByText('75')).toBeInTheDocument();
  });

  it('excludes SIN_DATOS from the score denominator', () => {
    render(
      <SaludPredictivaSemaforo
        states={{
          A: state('A', 'SANO'),
          B: state('B', 'SIN_DATOS'),
          C: state('C', 'SIN_DATOS'),
        }}
      />,
    );
    // SIN_DATOS excluded → only A counts → score 100
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('defaults to score 100 when there are no evaluable equipos', () => {
    render(
      <SaludPredictivaSemaforo
        states={{ A: null, B: state('B', 'SIN_DATOS') }}
      />,
    );
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('renders a legend line per state with its count', () => {
    render(
      <SaludPredictivaSemaforo
        states={{
          A: state('A', 'SANO'),
          B: state('B', 'OBSERVADO'),
          C: state('C', 'CRITICO'),
        }}
      />,
    );
    expect(screen.getByText(/1 sano/)).toBeInTheDocument();
    expect(screen.getByText(/1 observado/)).toBeInTheDocument();
    expect(screen.getByText(/1 crítico/)).toBeInTheDocument();
  });
});
