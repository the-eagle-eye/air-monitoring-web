'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { usePolling } from '@/hooks/usePolling';
import HealthSemaforo from '@/components/dashboard/HealthSemaforo';
import KpiCards from '@/components/dashboard/KpiCards';
import EquipoGrid from '@/components/dashboard/EquipoGrid';
import RiskDistributionChart from '@/components/dashboard/RiskDistributionChart';
import PredictionTrendsChart from '@/components/dashboard/PredictionTrendsChart';
import SensorTrendsChart from '@/components/dashboard/SensorTrendsChart';
import RecentAlerts from '@/components/dashboard/RecentAlerts';
import IncidenciasSummary from '@/components/dashboard/IncidenciasSummary';
import ProximasCalibraciones from '@/components/dashboard/ProximasCalibraciones';
import { fetchDashboardData, fetchEquipoLecturas } from '@/lib/api/dashboard';
import { fetchPredicciones } from '@/lib/api/predicciones';
import { fetchIncidencias, fetchCalibracionesOps } from '@/lib/api/ops';
import type { DashboardData, KpiData, RiskDistribution } from '@/types/dashboard';
import type { LecturaIoT } from '@/types/lectura';
import type { Prediccion } from '@/types/prediccion';
import type { Incidencia, CalibracionOps } from '@/types/ops';

function computeKpis(data: DashboardData): KpiData {
  const predictions = Object.values(data.latestPredictions);
  const alertasAltas = data.alertas.filter(
    (a) => (a.nivel_riesgo === 'alta' || a.nivel_riesgo === 'media') && a.estado === 'activa',
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
  const [predicciones, setPredicciones] = useState<Prediccion[]>([]);
  const [prediccionesLoading, setPrediccionesLoading] = useState(false);
  const [openIncidencias, setOpenIncidencias] = useState<Incidencia[]>([]);
  const [pendingCalibraciones, setPendingCalibraciones] = useState<CalibracionOps[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const selectedEquipoRef = useRef(selectedEquipo);
  selectedEquipoRef.current = selectedEquipo;

  const loadDashboard = useCallback((silent = false) => {
    if (!silent) setLoading(true);
    fetchDashboardData()
      .then((data) => {
        setDashData(data);
        if (!selectedEquipoRef.current && data.equipos.length > 0) {
          setSelectedEquipo(data.equipos[0].device_id);
        }
        setLastUpdated(new Date());
      })
      .catch((err) => { if (!silent) setError(err.message); })
      .finally(() => { if (!silent) setLoading(false); });

    Promise.all([
      fetchIncidencias({ tipo: 'correctiva', estado: 'pendiente', page_size: 50 }),
      fetchIncidencias({ tipo: 'correctiva', estado: 'en_ejecucion', page_size: 50 }),
    ])
      .then(([pend, ejec]) => setOpenIncidencias([...pend.items, ...ejec.items]))
      .catch(() => {});

    fetchCalibracionesOps({ page_size: 100 })
      .then((res) => setPendingCalibraciones(res.items.filter((c) => !c.fecha_calibracion && c.incidencia_estado !== 'finalizado' && c.incidencia_estado !== 'cancelado')))
      .catch(() => {});
  }, []);

  const loadEquipoData = useCallback((silent = false) => {
    const equipo = selectedEquipoRef.current;
    if (!equipo) return;
    if (!silent) setLecturasLoading(true);
    fetchEquipoLecturas(equipo)
      .then(setLecturas)
      .catch(() => setLecturas([]))
      .finally(() => { if (!silent) setLecturasLoading(false); });

    if (!silent) setPrediccionesLoading(true);
    fetchPredicciones(equipo, 1, 200)
      .then((res) => setPredicciones(res.items))
      .catch(() => setPredicciones([]))
      .finally(() => { if (!silent) setPrediccionesLoading(false); });
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  useEffect(() => {
    if (!selectedEquipo) {
      setLecturas([]);
      setPredicciones([]);
      return;
    }
    loadEquipoData();
  }, [selectedEquipo, loadEquipoData]);

  usePolling(() => { loadDashboard(true); loadEquipoData(true); }, 30_000);

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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Dashboard de Monitoreo
        </h1>
        {lastUpdated && (
          <span className="text-xs text-zinc-400">
            Actualizado: {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>

      <HealthSemaforo
        predictions={dashData.latestPredictions}
        totalEquipos={dashData.equipos.length}
        incidenciasAbiertas={openIncidencias}
      />

      <KpiCards data={kpis} />

      <EquipoGrid
        equipos={dashData.equipos}
        predictions={dashData.latestPredictions}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RiskDistributionChart data={riskDist} />
        <RecentAlerts alertas={dashData.alertas} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <IncidenciasSummary incidencias={openIncidencias} />
        <ProximasCalibraciones calibraciones={pendingCalibraciones} />
      </div>

      <PredictionTrendsChart
        predicciones={predicciones}
        loading={prediccionesLoading}
        selectedEquipo={selectedEquipo}
        equipoOptions={equipoOptions}
        onEquipoChange={setSelectedEquipo}
      />

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
