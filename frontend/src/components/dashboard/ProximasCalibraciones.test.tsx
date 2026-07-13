import { render, screen } from '@testing-library/react';
import ProximasCalibraciones from './ProximasCalibraciones';
import type { CalibracionOps } from '@/types/ops';

function cal(overrides: Partial<CalibracionOps> = {}): CalibracionOps {
  return {
    id: 1,
    incidencia_id: null,
    device_id: 'T101',
    fecha_calibracion: null,
    nota: null,
    certificado_url: null,
    proveedor_id: null,
    estado: 'pendiente',
    incidencia_estado: null,
    created_at: '2026-07-12T00:00:00Z',
    ...overrides,
  } as CalibracionOps;
}

describe('ProximasCalibraciones', () => {
  it('renders the empty state when there are no calibraciones', () => {
    render(<ProximasCalibraciones calibraciones={[]} />);
    expect(
      screen.getByText('No hay calibraciones pendientes'),
    ).toBeInTheDocument();
    expect(screen.getByText('0 pendientes')).toBeInTheDocument();
  });

  it('shows the total count and slices to 8 items', () => {
    const items = Array.from({ length: 10 }, (_, i) =>
      cal({ id: i + 1, device_id: `T10${i}` }),
    );
    render(<ProximasCalibraciones calibraciones={items} />);
    expect(screen.getByText('10 pendientes')).toBeInTheDocument();
    expect(screen.getByText('T100')).toBeInTheDocument();
    expect(screen.queryByText('T108')).not.toBeInTheDocument();
  });

  it('renders the em-dash when nota is missing', () => {
    render(<ProximasCalibraciones calibraciones={[cal({ nota: null })]} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('renders the nota when present', () => {
    render(
      <ProximasCalibraciones calibraciones={[cal({ nota: 'programar' })]} />,
    );
    expect(screen.getByText('programar')).toBeInTheDocument();
  });
});
