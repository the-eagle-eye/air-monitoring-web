import Badge from './Badge';

const STATUS_MAP: Record<
  string,
  {
    label: string;
    variant: 'success' | 'warning' | 'danger' | 'info' | 'default';
  }
> = {
  activo: { label: 'Activo', variant: 'success' },
  inactivo: { label: 'Inactivo', variant: 'default' },
  en_revision: { label: 'En Revision', variant: 'warning' },
  pendiente: { label: 'Pendiente', variant: 'info' },
  en_ejecucion: { label: 'En Ejecucion', variant: 'warning' },
  finalizado: { label: 'Finalizado', variant: 'success' },
  cancelado: { label: 'Cancelado', variant: 'danger' },
};

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_MAP[status] ?? {
    label: status,
    variant: 'default' as const,
  };
  return <Badge label={config.label} variant={config.variant} />;
}
