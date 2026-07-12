import { render, screen } from '@testing-library/react';
import StatusBadge from './StatusBadge';
import Badge from './Badge';

describe('Badge', () => {
  it('renders its label', () => {
    render(<Badge label="Hola" />);
    expect(screen.getByText('Hola')).toBeInTheDocument();
  });

  it('applies the variant classes', () => {
    render(<Badge label="Peligro" variant="danger" />);
    const el = screen.getByText('Peligro');
    expect(el.className).toContain('bg-red-100');
    expect(el.className).toContain('text-red-800');
  });

  it('defaults to the default variant', () => {
    render(<Badge label="Neutro" />);
    expect(screen.getByText('Neutro').className).toContain('bg-zinc-100');
  });
});

describe('StatusBadge', () => {
  it.each([
    ['activo', 'Activo'],
    ['pendiente', 'Pendiente'],
    ['en_ejecucion', 'En Ejecucion'],
    ['finalizado', 'Finalizado'],
    ['cancelado', 'Cancelado'],
  ])('maps ITIL status "%s" to label "%s"', (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('falls back to the raw status with default variant when unknown', () => {
    render(<StatusBadge status="estado_raro" />);
    const el = screen.getByText('estado_raro');
    expect(el).toBeInTheDocument();
    expect(el.className).toContain('bg-zinc-100');
  });
});
