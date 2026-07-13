import { render, screen } from '@testing-library/react';
import IncidenciasSummary from './IncidenciasSummary';
import type { Incidencia } from '@/types/ops';

function inc(overrides: Partial<Incidencia> = {}): Incidencia {
  return {
    id: 1,
    device_id: 'T101',
    tipo: 'correctiva',
    descripcion: null,
    estado: 'pendiente',
    prioridad: 'media',
    responsable_id: null,
    created_at: new Date().toISOString(),
    updated_at: null,
    ...overrides,
  } as Incidencia;
}

describe('IncidenciasSummary', () => {
  it('renders the empty state when there are no incidencias', () => {
    render(<IncidenciasSummary incidencias={[]} />);
    expect(
      screen.getByText('No hay incidencias correctivas abiertas'),
    ).toBeInTheDocument();
    expect(screen.getByText('0 Correctivas')).toBeInTheDocument();
  });

  it('shows the total count and up to 8 most recent items', () => {
    const items: Incidencia[] = Array.from({ length: 10 }, (_, i) =>
      inc({
        id: i + 1,
        device_id: `T10${i}`,
        created_at: new Date(Date.now() - i * 60_000).toISOString(),
      }),
    );
    render(<IncidenciasSummary incidencias={items} />);
    expect(screen.getByText('10 Correctivas')).toBeInTheDocument();
    // Sorted desc → T100 (newest) is first, T109 (oldest) is trimmed.
    expect(screen.getByText('T100')).toBeInTheDocument();
    expect(screen.queryByText('T108')).not.toBeInTheDocument();
    expect(screen.queryByText('T109')).not.toBeInTheDocument();
  });

  it('capitalizes prioridad in the Badge', () => {
    render(<IncidenciasSummary incidencias={[inc({ prioridad: 'alta' })]} />);
    expect(screen.getByText('Alta')).toBeInTheDocument();
  });

  it('formats the relative timestamp in minutes/hours/days', () => {
    const items = [
      inc({
        id: 1,
        device_id: 'A',
        created_at: new Date(Date.now() - 5 * 60_000).toISOString(),
      }),
      inc({
        id: 2,
        device_id: 'B',
        created_at: new Date(Date.now() - 3 * 3_600_000).toISOString(),
      }),
      inc({
        id: 3,
        device_id: 'C',
        created_at: new Date(Date.now() - 4 * 86_400_000).toISOString(),
      }),
    ];
    render(<IncidenciasSummary incidencias={items} />);
    expect(screen.getByText(/hace 5m/)).toBeInTheDocument();
    expect(screen.getByText(/hace 3h/)).toBeInTheDocument();
    expect(screen.getByText(/hace 4d/)).toBeInTheDocument();
  });

  it('links to the incidencia detail page', () => {
    render(<IncidenciasSummary incidencias={[inc({ id: 42 })]} />);
    const link = screen
      .getAllByRole('link')
      .find((a) => a.getAttribute('href') === '/incidencias/42');
    expect(link).toBeDefined();
  });
});
