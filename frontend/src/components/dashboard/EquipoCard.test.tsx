import { render, screen } from '@testing-library/react';
import EquipoCard from './EquipoCard';
import type { Equipo } from '@/types/lectura';
import type { HealthDeviceState } from '@/types/healthMonitor';

function equipo(overrides: Partial<Equipo> = {}): Equipo {
  return {
    id: 1,
    device_id: 'T101',
    nombre: null,
    tipo: null,
    ubicacion: null,
    estado: 'activo',
    serie: null,
    codigo_interno: null,
    modelo: null,
    marca: null,
    fecha_ingreso: null,
    rango_medicion: null,
    parametro_medicion: null,
    foto_equipo: null,
    datalogger_id: null,
    fecha_registro: '2026-07-12T00:00:00Z',
    fecha_actualizacion: null,
    ...overrides,
  } as Equipo;
}

function health(overrides: Partial<HealthDeviceState> = {}): HealthDeviceState {
  return {
    device_id: 'T101',
    health_state: 'SANO',
    last_recon_error: null,
    theta: null,
    hours_since_prev: 0.5,
    updated_at: '2026-07-12T00:00:00Z',
    ...overrides,
  };
}

describe('EquipoCard', () => {
  it('renders device_id and the default nombre fallback', () => {
    render(<EquipoCard equipo={equipo()} />);
    expect(screen.getByText('T101')).toBeInTheDocument();
    expect(screen.getByText('Equipo de medicion')).toBeInTheDocument();
  });

  it('prefers nombre → tipo → fallback in that order', () => {
    render(<EquipoCard equipo={equipo({ tipo: 'SO2 analyzer' })} />);
    expect(screen.getByText('SO2 analyzer')).toBeInTheDocument();

    const { rerender } = render(
      <EquipoCard equipo={equipo({ nombre: 'Ilo-01', tipo: 'X' })} />,
    );
    expect(screen.getByText('Ilo-01')).toBeInTheDocument();
    rerender(<EquipoCard equipo={equipo()} />);
  });

  it('falls back to the "activo" estado styling when the estado is unknown', () => {
    render(<EquipoCard equipo={equipo({ estado: 'estado_raro' })} />);
    expect(screen.getByText('Activo')).toBeInTheDocument();
  });

  it('shows the "Sin datos de salud" placeholder when no health is provided', () => {
    render(<EquipoCard equipo={equipo()} />);
    expect(screen.getByText('Sin datos de salud aún')).toBeInTheDocument();
  });

  it('renders minute-scale uptime when hours_since_prev < 1', () => {
    render(
      <EquipoCard
        equipo={equipo()}
        health={health({ hours_since_prev: 0.5 })}
      />,
    );
    expect(screen.getByText('30 min')).toBeInTheDocument();
  });

  it('renders hour-scale uptime when hours_since_prev ≥ 1', () => {
    render(
      <EquipoCard
        equipo={equipo()}
        health={health({ hours_since_prev: 4.2 })}
      />,
    );
    expect(screen.getByText('4.2 h')).toBeInTheDocument();
  });

  it('omits uptime + action for SIN_DATOS health', () => {
    render(
      <EquipoCard
        equipo={equipo()}
        health={health({ health_state: 'SIN_DATOS' })}
      />,
    );
    expect(screen.queryByText('Operando sin corte')).not.toBeInTheDocument();
    // Suggested action still renders.
    expect(
      screen.getByText('Revisar PC / energía / transmisión.'),
    ).toBeInTheDocument();
  });

  it('shows the singular incidencias badge when count = 1', () => {
    render(
      <EquipoCard
        equipo={equipo()}
        health={health()}
        incidenciasAbiertas={1}
      />,
    );
    expect(screen.getByText('1 incidencia abierta')).toBeInTheDocument();
  });

  it('shows the plural incidencias badge when count > 1', () => {
    render(
      <EquipoCard
        equipo={equipo()}
        health={health()}
        incidenciasAbiertas={3}
      />,
    );
    expect(screen.getByText('3 incidencias abiertas')).toBeInTheDocument();
  });

  it('links to the equipo detail page', () => {
    render(<EquipoCard equipo={equipo()} />);
    const link = screen.getByRole('link');
    expect(link.getAttribute('href')).toBe('/equipos/T101');
  });
});
