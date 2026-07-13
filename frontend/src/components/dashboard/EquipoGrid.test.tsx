import { render, screen } from '@testing-library/react';
import EquipoGrid from './EquipoGrid';
import type { Equipo } from '@/types/lectura';
import type { HealthDeviceState } from '@/types/healthMonitor';
import type { Incidencia } from '@/types/ops';

function eq(id: string, extra: Partial<Equipo> = {}): Equipo {
  return {
    id: Number(id.replace(/\D/g, '')) || 1,
    device_id: id,
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
    fecha_registro: '2026-01-01T00:00:00Z',
    fecha_actualizacion: null,
    ...extra,
  } as Equipo;
}

function hs(state: HealthDeviceState['health_state']): HealthDeviceState {
  return {
    device_id: 'x',
    health_state: state,
    last_recon_error: null,
    theta: null,
    hours_since_prev: null,
    updated_at: '2026-07-12T00:00:00Z',
  };
}

describe('EquipoGrid', () => {
  it('renders the empty state when equipos is empty', () => {
    render(<EquipoGrid equipos={[]} />);
    expect(screen.getByText('No hay equipos registrados')).toBeInTheDocument();
  });

  it('sorts equipos by health severity: CRITICO before SANO', () => {
    const equipos = [eq('T-SANO'), eq('T-CRIT'), eq('T-OBS')];
    const healthStates = {
      'T-SANO': hs('SANO'),
      'T-CRIT': hs('CRITICO'),
      'T-OBS': hs('OBSERVADO'),
    };
    render(<EquipoGrid equipos={equipos} healthStates={healthStates} />);
    const cards = screen.getAllByRole('link');
    // Order should be CRITICO, OBSERVADO, SANO
    expect(cards[0].getAttribute('href')).toBe('/equipos/T-CRIT');
    expect(cards[1].getAttribute('href')).toBe('/equipos/T-OBS');
    expect(cards[2].getAttribute('href')).toBe('/equipos/T-SANO');
  });

  it('places equipos with unknown health at the end', () => {
    const equipos = [eq('T-NO-HEALTH'), eq('T-CRIT')];
    render(
      <EquipoGrid
        equipos={equipos}
        healthStates={{ 'T-CRIT': hs('CRITICO') }}
      />,
    );
    const cards = screen.getAllByRole('link');
    expect(cards[0].getAttribute('href')).toBe('/equipos/T-CRIT');
    expect(cards[1].getAttribute('href')).toBe('/equipos/T-NO-HEALTH');
  });

  it('counts open incidencias per device and forwards to the card', () => {
    const incidencias: Incidencia[] = [
      { id: 1, device_id: 'T-1' } as Incidencia,
      { id: 2, device_id: 'T-1' } as Incidencia,
      { id: 3, device_id: 'T-2' } as Incidencia,
    ];
    render(
      <EquipoGrid
        equipos={[eq('T-1'), eq('T-2')]}
        openIncidencias={incidencias}
      />,
    );
    expect(screen.getByText('2 incidencias abiertas')).toBeInTheDocument();
    expect(screen.getByText('1 incidencia abierta')).toBeInTheDocument();
  });
});
