'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { usePolling } from '@/hooks/usePolling';
import SaludPredictivaSemaforo from '@/components/dashboard/SaludPredictivaSemaforo';
import EquiposSinTransmision from '@/components/dashboard/EquiposSinTransmision';
import KpiCards from '@/components/dashboard/KpiCards';
import EquipoGrid from '@/components/dashboard/EquipoGrid';
import RiskDistributionChart from '@/components/dashboard/RiskDistributionChart';
import AnomalyTrendsChart from '@/components/dashboard/AnomalyTrendsChart';
import SensorTrendsChart from '@/components/dashboard/SensorTrendsChart';
import EquiposAtencion from '@/components/dashboard/EquiposAtencion';
import IncidenciasSummary from '@/components/dashboard/IncidenciasSummary';
import ProximasCalibraciones from '@/components/dashboard/ProximasCalibraciones';
import EquiposReincidentes from '@/components/dashboard/EquiposReincidentes';
import { useAuth } from '@/lib/auth';
import { fetchDashboardData, fetchEquipoLecturas } from '@/lib/api/dashboard';
import { fetchIncidencias, fetchCalibracionesOps } from '@/lib/api/ops';
import { fetchHealthStates } from '@/lib/api/healthMonitor';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';
import type { HealthDeviceState, HealthState } from '@/types/healthMonitor';
import type {
  DashboardData,
  KpiData,
  RiskDistribution,
} from '@/types/dashboard';
import type { LecturaIoT } from '@/types/lectura';
import type { Incidencia, CalibracionOps } from '@/types/ops';

const ANOMALOUS: HealthState[] = ['OBSERVADO', 'EN_RIESGO', 'CRITICO'];
const DIST_ORDER: HealthState[] = [
  'SANO',
  'OBSERVADO',
  'EN_RIESGO',
  'CRITICO',
  'SIN_DATOS',
];

// KPIs del modelo ensemble (no supervisado): equipos monitoreados, equipos con
// anomalía (observado/riesgo/crítico), incidencias abiertas y sin transmisión.
function computeKpis(
  data: DashboardData,
  healthStates: Record<string, HealthDeviceState | null>,
  openIncidencias: Incidencia[],
): KpiData {
  const states = Object.values(healthStates).filter(
    (s): s is HealthDeviceState => s !== null,
  );
  const anomalias24h = states.filter((s) =>
    ANOMALOUS.includes(s.health_state),
  ).length;
  const sinTransmision = states.filter(
    (s) =>
      s.health_state === 'SIN_DATOS' ||
      s.transmission_state === 'SIN_TRANSMISION',
  ).length;

  return {
    totalEquipos: data.equipos.length,
    anomalias24h,
    incidenciasAbiertas: openIncidencias.length,
    sinTransmision,
  };
}

// Distribución por estado de salud del ensemble (reemplaza la distribución por
// risk_level del RF).
function computeHealthDistribution(
  healthStates: Record<string, HealthDeviceState | null>,
): RiskDistribution[] {
  const counts: Record<HealthState, number> = {
    SANO: 0,
    OBSERVADO: 0,
    EN_RIESGO: 0,
    CRITICO: 0,
    SIN_DATOS: 0,
  };
  Object.values(healthStates).forEach((s) => {
    if (s) counts[s.health_state] = (counts[s.health_state] ?? 0) + 1;
  });
  return DIST_ORDER.map((st) => ({
    name: HEALTH_STATE_CONFIG[st].label,
    value: counts[st],
    color: HEALTH_STATE_CONFIG[st].color,
  }));
}

export default function DashboardPage() {
  const { user } = useAuth();
  // Coordinador/admin gestionan problemas (crear a partir de reincidentes).
  const canCrearProblema =
    user?.rol === 'coordinador' || user?.rol === 'administrador';
  const [dashData, setDashData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedEquipo, setSelectedEquipo] = useState('');
  const [lecturas, setLecturas] = useState<LecturaIoT[]>([]);
  const [lecturasLoading, setLecturasLoading] = useState(false);
  const [openIncidencias, setOpenIncidencias] = useState<Incidencia[]>([]);
  const [pendingCalibraciones, setPendingCalibraciones] = useState<
    CalibracionOps[]
  >([]);
  const [healthStates, setHealthStates] = useState<
    Record<string, HealthDeviceState | null>
  >({});
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
        // Salud predictiva (ensemble) por equipo — tolerante a fallos por equipo.
        fetchHealthStates(data.equipos.map((e) => e.device_id))
          .then(setHealthStates)
          .catch(() => {});
      })
      .catch((err) => {
        if (!silent) setError(err.message);
      })
      .finally(() => {
        if (!silent) setLoading(false);
      });

    Promise.all([
      fetchIncidencias({
        tipo: 'correctiva',
        estado: 'pendiente',
        page_size: 50,
      }),
      fetchIncidencias({
        tipo: 'correctiva',
        estado: 'en_ejecucion',
        page_size: 50,
      }),
    ])
      .then(([pend, ejec]) =>
        setOpenIncidencias([...pend.items, ...ejec.items]),
      )
      .catch(() => {});

    fetchCalibracionesOps({ page_size: 100 })
      .then((res) =>
        setPendingCalibraciones(
          res.items.filter(
            (c) =>
              !c.fecha_calibracion &&
              c.incidencia_estado !== 'finalizado' &&
              c.incidencia_estado !== 'cancelado',
          ),
        ),
      )
      .catch(() => {});
  }, []);

  const loadEquipoData = useCallback((silent = false) => {
    const equipo = selectedEquipoRef.current;
    if (!equipo) return;
    if (!silent) setLecturasLoading(true);
    fetchEquipoLecturas(equipo)
      .then(setLecturas)
      .catch(() => setLecturas([]))
      .finally(() => {
        if (!silent) setLecturasLoading(false);
      });
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedEquipo) {
      setLecturas([]);
      return;
    }
    loadEquipoData();
  }, [selectedEquipo, loadEquipoData]);

  usePolling(() => {
    loadDashboard(true);
    loadEquipoData(true);
  }, 30_000);

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

  const kpis = computeKpis(dashData, healthStates, openIncidencias);
  const healthDist = computeHealthDistribution(healthStates);
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

      {/* Semáforo único: Salud Predictiva (ensemble AE+IF+AND). El modelo RF
          (RUL, predicciones, alertas) se retiró — el sistema es el ensemble. */}
      <SaludPredictivaSemaforo states={healthStates} />

      <EquiposSinTransmision states={healthStates} />

      <KpiCards data={kpis} />

      <EquipoGrid
        equipos={dashData.equipos}
        healthStates={healthStates}
        openIncidencias={openIncidencias}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RiskDistributionChart data={healthDist} />
        <EquiposAtencion
          states={healthStates}
          openIncidencias={openIncidencias}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <IncidenciasSummary incidencias={openIncidencias} />
        <EquiposReincidentes
          canCrear={canCrearProblema}
          onProblemaCreado={() => loadDashboard(true)}
        />
      </div>

      <ProximasCalibraciones calibraciones={pendingCalibraciones} />

      <AnomalyTrendsChart
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
