import { render, screen } from '@testing-library/react';
import LecturasTable from './LecturasTable';
import type { LecturaIoT } from '@/types/lectura';

function lect(overrides: Partial<LecturaIoT> = {}): LecturaIoT {
  return {
    id: 1,
    device_id: 1,
    equipo_device_id: 'T101',
    timestamp_lectura: '2026-07-12T15:00:00Z',
    procesado: true,
    created_at: '2026-07-12T15:00:00Z',
    so2_ppb: 2.3456,
    h2s_ppb: null,
    ...overrides,
  } as LecturaIoT;
}

describe('LecturasTable', () => {
  it('renders every sensor column header', () => {
    render(<LecturasTable lecturas={[]} />);
    expect(screen.getByText('SO₂ (ppb)')).toBeInTheDocument();
    expect(screen.getByText('H₂S (ppb)')).toBeInTheDocument();
    expect(screen.getByText('Timestamp')).toBeInTheDocument();
    expect(screen.getByText('UV Lamp')).toBeInTheDocument();
  });

  it('formats numeric values with 2 decimals and null as em-dash', () => {
    render(<LecturasTable lecturas={[lect()]} />);
    expect(screen.getByText('2.35')).toBeInTheDocument();
    // At least one em-dash (H₂S is null) shows.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('reads sensor values from the JSONB `sensors` shape', () => {
    const l = lect({
      so2_ppb: undefined,
      sensors: { SO2_ppb: 9.87 },
    } as LecturaIoT);
    render(<LecturasTable lecturas={[l]} />);
    expect(screen.getByText('9.87')).toBeInTheDocument();
  });

  it('renders equipo_device_id per row', () => {
    render(<LecturasTable lecturas={[lect({ equipo_device_id: 'T-XYZ' })]} />);
    expect(screen.getByText('T-XYZ')).toBeInTheDocument();
  });

  it('renders empty-state row when no lecturas', () => {
    render(<LecturasTable lecturas={[]} />);
    expect(screen.getByText('No hay datos disponibles')).toBeInTheDocument();
  });
});
