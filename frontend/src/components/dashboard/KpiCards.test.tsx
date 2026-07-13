import { render, screen } from '@testing-library/react';
import KpiCards from './KpiCards';
import type { KpiData } from '@/types/dashboard';

const kpis: KpiData = {
  totalEquipos: 5,
  anomalias24h: 2,
  incidenciasAbiertas: 3,
  sinTransmision: 1,
} as KpiData;

describe('KpiCards', () => {
  it('renders each of the four KPI labels', () => {
    render(<KpiCards data={kpis} />);
    expect(screen.getByText('Equipos monitoreados')).toBeInTheDocument();
    expect(screen.getByText('Equipos con anomalía')).toBeInTheDocument();
    expect(screen.getByText('Incidencias abiertas')).toBeInTheDocument();
    expect(screen.getByText('Sin transmisión')).toBeInTheDocument();
  });

  it('binds each KPI value from the data prop', () => {
    render(<KpiCards data={kpis} />);
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });
});
