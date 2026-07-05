'use client';

import { useEffect, useState } from 'react';
import ReconErrorChart from './ReconErrorChart';
import { fetchHealthReadings } from '@/lib/api/healthMonitor';
import type { HealthReadingPoint } from '@/types/healthMonitor';

interface AnomalyTrendsChartProps {
  selectedEquipo: string;
  equipoOptions: { device_id: string; label: string }[];
  onEquipoChange: (deviceId: string) => void;
}

// Tendencia de anomalías del ensemble (recon_error + θ) por equipo. Reemplaza a
// "Tendencia de Predicciones" (RF: RUL / prob. falla), retirada con el RF.
export default function AnomalyTrendsChart({
  selectedEquipo,
  equipoOptions,
  onEquipoChange,
}: AnomalyTrendsChartProps) {
  const [points, setPoints] = useState<HealthReadingPoint[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedEquipo) {
      setPoints([]);
      return;
    }
    setLoading(true);
    fetchHealthReadings(selectedEquipo)
      .then((res) => setPoints(res.points))
      .catch(() => setPoints([]))
      .finally(() => setLoading(false));
  }, [selectedEquipo]);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Tendencia de Anomalías
        </h2>
        <select
          value={selectedEquipo}
          onChange={(e) => onEquipoChange(e.target.value)}
          className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        >
          <option value="">Seleccionar equipo</option>
          {equipoOptions.map((eq) => (
            <option key={eq.device_id} value={eq.device_id}>
              {eq.label}
            </option>
          ))}
        </select>
      </div>
      <ReconErrorChart points={points} loading={loading} />
    </div>
  );
}
