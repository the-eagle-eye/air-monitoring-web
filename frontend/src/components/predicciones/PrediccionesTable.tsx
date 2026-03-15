'use client';

import DataTable from '@/components/ui/DataTable';
import RiskBadge from '@/components/ui/RiskBadge';
import type { Prediccion } from '@/types/prediccion';

interface PrediccionesTableProps {
  predicciones: Prediccion[];
}

export default function PrediccionesTable({
  predicciones,
}: PrediccionesTableProps) {
  const columns = [
    { key: 'device_id', header: 'Equipo' },
    {
      key: 'prediction_timestamp',
      header: 'Fecha',
      render: (p: Prediccion) =>
        new Date(p.prediction_timestamp).toLocaleString(),
    },
    {
      key: 'failure_probability',
      header: 'Prob. Falla',
      render: (p: Prediccion) => `${(p.failure_probability * 100).toFixed(1)}%`,
    },
    {
      key: 'remaining_useful_life_days',
      header: 'RUL (dias)',
      render: (p: Prediccion) => String(p.remaining_useful_life_days),
    },
    {
      key: 'risk_level',
      header: 'Riesgo',
      render: (p: Prediccion) => <RiskBadge level={p.risk_level} />,
    },
    { key: 'model_version', header: 'Modelo' },
  ];

  return (
    <DataTable columns={columns} data={predicciones} keyExtractor={(p) => p.id} />
  );
}
