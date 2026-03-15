'use client';

import { useEffect, useState } from 'react';
import KpiCards from '@/components/dashboard/KpiCards';
import EquipoGrid from '@/components/dashboard/EquipoGrid';
import RiskDistributionChart from '@/components/dashboard/RiskDistributionChart';
import SensorTrendsChart from '@/components/dashboard/SensorTrendsChart';
import RecentAlerts from '@/components/dashboard/RecentAlerts';
import { fetchDashboardData, fetchEquipoLecturas } from '@/lib/api/dashboard';
import type { DashboardData, KpiData, RiskDistribution } from '@/types/dashboard';
import type { LecturaIoT } from '@/types/lectura';

function computeKpis(data: DashboardData): KpiData {
  const predictions = Object.values(data.latestPredictions);
  const alertasAltas = data.alertas.filter(
    (a) => a.nivel_riesgo === 'alta' && a.estado === 'activa',
  ).length;
  const rulValues = predictions.map((p) => p.remaining_useful_life_days);
  const rulPromedio =
    rulValues.length > 0
      ? Math.round(rulValues.reduce((a, b) => a + b, 0) / rulValues.length)
      : 0;

  return {
    totalEquipos: data.equipos.length,
    alertasAltas,
    rulPromedio,
    prediccionesRecientes: predictions.length,
  };
}

function computeRiskDistribution(data: DashboardData): RiskDistribution[] {
  const counts = { alta: 0, media: 0, baja: 0 };
  Object.values(data.latestPredictions).forEach((p) => {
    counts[p.risk_level] = (counts[p.risk_level] ?? 0) + 1;
  });
  return [
    { name: 'Alta', value: counts.alta, color: '#ef4444' },
    { name: 'Media', value: counts.media, color: '#eab308' },
    { name: 'Baja', value: counts.baja, color: '#22c55e' },
  ];
}

export default function DashboardPage() {
  const [dashData, setDashData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedEquipo, setSelectedEquipo] = useState('');
  const [lecturas, setLecturas] = useState<LecturaIoT[]>([]);
  const [lecturasLoading, setLecturasLoading] = useState(false);

  useEffect(() => {
    fetchDashboardData()
      .then((data) => {
        setDashData(data);
        if (data.equipos.length > 0) {
          setSelectedEquipo(data.equipos[0].device_id);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedEquipo) {
      setLecturas([]);
      return;
    }
    setLecturasLoading(true);
    fetchEquipoLecturas(selectedEquipo)
      .then(setLecturas)
      .catch(() => setLecturas([]))
      .finally(() => setLecturasLoading(false));
  }, [selectedEquipo]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="py-12 text-center text-zinc-400">
          Cargando dashboard...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!dashData) return null;

  const kpis = computeKpis(dashData);
  const riskDist = computeRiskDistribution(dashData);
  const equipoOptions = dashData.equipos.map((eq) => ({
    device_id: eq.device_id,
    label: `${eq.device_id}${eq.nombre ? ` - ${eq.nombre}` : ''}`,
  }));

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
        Dashboard de Monitoreo
      </h1>

      <KpiCards data={kpis} />

      <EquipoGrid
        equipos={dashData.equipos}
        predictions={dashData.latestPredictions}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RiskDistributionChart data={riskDist} />
        <RecentAlerts alertas={dashData.alertas} />
      </div>

      <SensorTrendsChart
        lecturas={lecturas}
        loading={lecturasLoading}
        selectedEquipo={selectedEquipo}
        equipoOptions={equipoOptions}
        onEquipoChange={setSelectedEquipo}
      />
    </div>
  );
}
