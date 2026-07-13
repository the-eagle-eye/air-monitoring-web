import { render, screen } from '@testing-library/react';
import EquiposTable from './EquiposTable';
import type { Equipo } from '@/types/lectura';

function eq(overrides: Partial<Equipo> = {}): Equipo {
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

describe('EquiposTable', () => {
  it('renders one row per equipo with headers', () => {
    render(<EquiposTable equipos={[eq({ nombre: 'Est-A' })]} />);
    expect(screen.getByText('Nombre')).toBeInTheDocument();
    expect(screen.getByText('Device ID')).toBeInTheDocument();
    expect(screen.getByText('Est-A')).toBeInTheDocument();
    expect(screen.getByText('T101')).toBeInTheDocument();
  });

  it('falls back to device_id when nombre is null', () => {
    render(
      <EquiposTable equipos={[eq({ nombre: null, device_id: 'T-XYZ' })]} />,
    );
    // device_id appears twice: in the "Nombre" fallback + "Device ID" column
    expect(screen.getAllByText('T-XYZ')).toHaveLength(2);
  });

  it('renders em-dashes for missing serie / ubicacion / parametro', () => {
    render(<EquiposTable equipos={[eq()]} />);
    // 3 em-dashes expected from the 3 null nullable string columns.
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(3);
  });

  it('shows the "Editar" and "Eliminar" actions by default', () => {
    render(<EquiposTable equipos={[eq()]} />);
    expect(screen.getByText('Ver')).toBeInTheDocument();
    expect(screen.getByText('Editar')).toBeInTheDocument();
    expect(screen.getByText('Eliminar')).toBeInTheDocument();
  });

  it('hides the "Editar" and "Eliminar" actions when readOnly', () => {
    render(<EquiposTable equipos={[eq()]} readOnly />);
    expect(screen.getByText('Ver')).toBeInTheDocument();
    expect(screen.queryByText('Editar')).not.toBeInTheDocument();
    expect(screen.queryByText('Eliminar')).not.toBeInTheDocument();
  });

  it('renders the empty-state row when no equipos', () => {
    render(<EquiposTable equipos={[]} />);
    expect(screen.getByText('No hay datos disponibles')).toBeInTheDocument();
  });
});
