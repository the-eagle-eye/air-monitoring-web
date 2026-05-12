'use client';

import DataTable from '@/components/ui/DataTable';
import RiskBadge from '@/components/ui/RiskBadge';
import Badge from '@/components/ui/Badge';
import type { Alerta } from '@/types/prediccion';

interface AlertasTableProps {
  alertas: Alerta[];
}

const ESTADO_VARIANT: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'default'> = {
  activa: 'danger',
  reconocida: 'warning',
  resuelta: 'success',
};

export default function AlertasTable({ alertas }: AlertasTableProps) {
  const columns = [
    { key: 'device_id', header: 'Equipo' },
    {
      key: 'created_at',
      header: 'Fecha',
      render: (a: Alerta) => new Date(a.created_at.endsWith('Z') ? a.created_at : a.created_at + 'Z').toLocaleString(),
    },
    {
      key: 'nivel_riesgo',
      header: 'Nivel',
      render: (a: Alerta) => <RiskBadge level={a.nivel_riesgo} />,
    },
    {
      key: 'estado',
      header: 'Estado',
      render: (a: Alerta) => (
        <Badge
          label={a.estado}
          variant={ESTADO_VARIANT[a.estado] ?? 'default'}
        />
      ),
    },
    {
      key: 'descripcion',
      header: 'Descripcion',
      render: (a: Alerta) => (
        <span className="max-w-xs truncate" title={a.descripcion ?? ''}>
          {a.descripcion ?? '—'}
        </span>
      ),
    },
  ];

  return (
    <DataTable columns={columns} data={alertas} keyExtractor={(a) => a.id} />
  );
}
