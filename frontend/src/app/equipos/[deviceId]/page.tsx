'use client';

import { useEffect, useState, useCallback } from 'react';
import { usePolling } from '@/hooks/usePolling';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { fetchEquipo, updateEquipo, fetchLecturas } from '@/lib/api/lecturas';
import { fetchIncidencias, fetchCalibracionesOps } from '@/lib/api/ops';
import { fetchHealthReadings } from '@/lib/api/healthMonitor';
import ReconErrorChart from '@/components/dashboard/ReconErrorChart';
import HealthStateBadge from '@/components/dashboard/HealthStateBadge';
import { readSensor } from '@/lib/sensorFields';
import EquipoForm from '@/components/equipos/EquipoForm';
import DataTable from '@/components/ui/DataTable';
import StatusBadge from '@/components/ui/StatusBadge';
import Badge from '@/components/ui/Badge';
import type { Equipo, LecturaIoT } from '@/types/lectura';
import type { Incidencia, CalibracionOps } from '@/types/ops';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';
import type { HealthReadingPoint } from '@/types/healthMonitor';

// --------------- helpers ---------------

const SENSOR_LINES = [
  { key: 'so2_ppb', name: 'SO2 (ppb)', color: '#8b5cf6' },
  { key: 'h2s_ppb', name: 'H2S (ppb)', color: '#06b6d4' },
  { key: 'reaction_temp', name: 'Temp. Reaccion', color: '#ef4444' },
  { key: 'box_temp', name: 'Temp. Caja', color: '#f97316' },
  { key: 'sample_flow', name: 'Flujo Muestra', color: '#22c55e' },
  { key: 'uv_lamp_intensity', name: 'Intensidad UV', color: '#eab308' },
];

function parseUTC(ts: string): Date {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z');
}

function formatTs(ts: string): string {
  const d = parseUTC(ts);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
}

const PRIORIDAD_VARIANT: Record<string, 'danger' | 'warning' | 'success'> = {
  alta: 'danger',
  media: 'warning',
  baja: 'success',
};

const CRITICIDAD_VARIANT: Record<string, 'danger' | 'warning' | 'success'> = {
  alta: 'danger',
  media: 'warning',
  baja: 'success',
};

// --------------- mini charts ---------------

const MiniSensorChart = dynamic(
  () =>
    import('recharts').then((mod) => {
      const { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } = mod;

      function Chart({ data }: { data: Record<string, unknown>[] }) {
        return (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#a1a1aa40" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} stroke="#a1a1aa" />
              <YAxis tick={{ fontSize: 10 }} stroke="#a1a1aa" />
              <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px', color: '#fafafa', fontSize: 12 }} />
              <Legend />
              {SENSOR_LINES.map((sensor) => (
                <Line key={sensor.key} type="monotone" dataKey={sensor.key} name={sensor.name} stroke={sensor.color} strokeWidth={2} dot={false} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );
      }
      return Chart;
    }),
  { ssr: false, loading: () => <div className="h-[250px]" /> },
);

// --------------- sub-components ---------------

function EquipoDetail({ equipo }: { equipo: Equipo }) {
  const fields = [
    { label: 'Device ID', value: equipo.device_id },
    { label: 'Nombre', value: equipo.nombre },
    { label: 'Tipo', value: equipo.tipo },
    { label: 'Ubicacion', value: equipo.ubicacion },
    { label: 'Serie', value: equipo.serie },
    { label: 'Marca', value: equipo.marca },
    { label: 'Modelo', value: equipo.modelo },
    { label: 'Parametro', value: equipo.parametro_medicion },
    { label: 'Rango', value: equipo.rango_medicion },
    { label: 'Estado', value: equipo.estado },
    { label: 'Fecha Ingreso', value: equipo.fecha_ingreso },
    { label: 'Fecha Registro', value: new Date(equipo.fecha_registro).toLocaleDateString() },
  ];

  const criticidad = equipo.criticidad ?? 'media';

  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-3">
      {fields.map((f) => (
        <div key={f.label}>
          <dt className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">
            {f.label}
          </dt>
          <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
            {f.value ?? '—'}
          </dd>
        </div>
      ))}
      <div>
        <dt className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">
          Criticidad
        </dt>
        <dd className="mt-0.5">
          <Badge
            label={criticidad.charAt(0).toUpperCase() + criticidad.slice(1)}
            variant={CRITICIDAD_VARIANT[criticidad] ?? 'default'}
          />
        </dd>
      </div>
    </div>
  );
}

const TABS = [
  { id: 'resumen', label: 'Resumen' },
  { id: 'salud', label: 'Salud' },
  { id: 'lecturas', label: 'Lecturas' },
  { id: 'historial', label: 'Historial' },
] as const;

type TabId = (typeof TABS)[number]['id'];

// --------------- main page ---------------

export default function EquipoDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const deviceId = params.deviceId as string;
  const mode = searchParams.get('mode') ?? 'view';

  const [equipo, setEquipo] = useState<Equipo | null>(null);
  const [correctivos, setCorrectivos] = useState<Incidencia[]>([]);
  const [incCalibraciones, setIncCalibraciones] = useState<Incidencia[]>([]);
  const [calibraciones, setCalibraciones] = useState<CalibracionOps[]>([]);
  const [lecturas, setLecturas] = useState<LecturaIoT[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('resumen');
  const [healthPoints, setHealthPoints] = useState<HealthReadingPoint[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadAllData = useCallback((silent = false) => {
    if (!silent) setLoading(true);
    // Salud predictiva (ensemble) — independiente, tolerante a 404/sin datos.
    fetchHealthReadings(deviceId, 300)
      .then((res) => setHealthPoints(res.points))
      .catch(() => setHealthPoints([]));
    Promise.all([
      fetchEquipo(deviceId),
      fetchIncidencias({ device_id: deviceId, tipo: 'correctiva', page_size: 100 }),
      fetchIncidencias({ device_id: deviceId, tipo: 'calibracion', page_size: 100 }),
      fetchLecturas(deviceId, 1, 100),
      fetchCalibracionesOps({ device_id: deviceId, page_size: 100 }),
    ])
      .then(([eq, corr, cal, lects, calOps]) => {
        setEquipo(eq);
        setCorrectivos(corr.items);
        setIncCalibraciones(cal.items);
        setLecturas(lects.items);
        setCalibraciones(calOps.items);
        setLastUpdated(new Date());
      })
      .catch((err) => { if (!silent) setError(err.message); })
      .finally(() => { if (!silent) setLoading(false); });
  }, [deviceId]);

  useEffect(() => { loadAllData(); }, [loadAllData]);

  usePolling(() => loadAllData(true), 30_000);

  async function handleUpdate(data: Record<string, unknown>) {
    await updateEquipo(deviceId, data);
    const updated = await fetchEquipo(deviceId);
    setEquipo(updated);
    router.replace(`/equipos/${deviceId}`);
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 text-center text-zinc-400">
        Cargando...
      </div>
    );
  }

  if (error || !equipo) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error ?? 'Equipo no encontrado'}
        </div>
      </div>
    );
  }

  const latestHealth = healthPoints.length > 0 ? healthPoints[healthPoints.length - 1] : null;
  const healthConfig = latestHealth ? HEALTH_STATE_CONFIG[latestHealth.health_state] : null;
  const anomalousReadings = healthPoints.filter((p) => p.and_alert).length;

  const sensorChartData = lecturas.map((l) => ({
    timestamp: formatTs(l.timestamp_lectura),
    so2_ppb: readSensor(l, 'so2_ppb'),
    h2s_ppb: readSensor(l, 'h2s_ppb'),
    reaction_temp: readSensor(l, 'reaction_temp'),
    box_temp: readSensor(l, 'box_temp'),
    sample_flow: readSensor(l, 'sample_flow'),
    uv_lamp_intensity: readSensor(l, 'uv_lamp_intensity'),
  }));

  // -- incidencias table columns --
  const incidenciaColumns = [
    { key: 'id', header: 'ID' },
    {
      key: 'estado',
      header: 'Estado',
      render: (item: Incidencia) => <StatusBadge status={item.estado} />,
    },
    {
      key: 'prioridad',
      header: 'Prioridad',
      render: (item: Incidencia) => (
        <Badge
          label={item.prioridad.charAt(0).toUpperCase() + item.prioridad.slice(1)}
          variant={PRIORIDAD_VARIANT[item.prioridad] ?? 'default'}
        />
      ),
    },
    {
      key: 'descripcion',
      header: 'Descripcion',
      render: (item: Incidencia) =>
        item.descripcion
          ? item.descripcion.length > 60
            ? item.descripcion.slice(0, 60) + '...'
            : item.descripcion
          : '—',
    },
    {
      key: 'created_at',
      header: 'Fecha',
      render: (item: Incidencia) => parseUTC(item.created_at).toLocaleDateString(),
    },
    {
      key: 'acciones',
      header: 'Accion',
      render: (item: Incidencia) => (
        <Link
          href={`/incidencias/${item.id}`}
          className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400"
        >
          Ver
        </Link>
      ),
    },
  ];

  // -- calibraciones table columns --
  const calibracionColumns = [
    { key: 'id', header: 'ID' },
    { key: 'device_id', header: 'Equipo' },
    {
      key: 'fecha_calibracion',
      header: 'Fecha Calibracion',
      render: (item: CalibracionOps) =>
        item.fecha_calibracion
          ? new Date(item.fecha_calibracion).toLocaleDateString()
          : <span className="text-amber-500">Pendiente</span>,
    },
    {
      key: 'nota',
      header: 'Nota',
      render: (item: CalibracionOps) =>
        item.nota
          ? item.nota.length > 50 ? item.nota.slice(0, 50) + '...' : item.nota
          : '—',
    },
    {
      key: 'certificado_url',
      header: 'Certificado',
      render: (item: CalibracionOps) =>
        item.certificado_url
          ? <span className="text-green-500">Si</span>
          : <span className="text-zinc-400">No</span>,
    },
    {
      key: 'created_at',
      header: 'Creada',
      render: (item: CalibracionOps) => parseUTC(item.created_at).toLocaleDateString(),
    },
    {
      key: 'acciones',
      header: 'Accion',
      render: (item: CalibracionOps) => (
        <Link
          href={`/calibraciones/${item.id}`}
          className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400"
        >
          Ver
        </Link>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
            Equipo: {equipo.nombre ?? equipo.device_id}
          </h1>
          {lastUpdated && (
            <span className="text-xs text-zinc-400">
              Actualizado: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {mode === 'view' && (
            <Link
              href={`/equipos/${deviceId}?mode=edit`}
              className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600"
            >
              Editar
            </Link>
          )}
          <Link
            href="/equipos"
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
          >
            Volver
          </Link>
        </div>
      </div>

      {/* Equipo details card */}
      <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        {mode === 'edit' ? (
          <EquipoForm
            initialData={equipo}
            mode="edit"
            onSubmit={handleUpdate}
            onCancel={() => router.replace(`/equipos/${deviceId}`)}
          />
        ) : (
          <EquipoDetail equipo={equipo} />
        )}
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-zinc-200 dark:border-zinc-700">
        <nav className="flex gap-4">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab: Resumen */}
      {activeTab === 'resumen' && (
        <div className="space-y-6">
          {/* Salud predictiva (ensemble no supervisado) */}
          <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
            <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              Salud Predictiva
            </h2>
            {!latestHealth || !healthConfig ? (
              <p className="text-sm text-zinc-400">Sin datos de salud disponibles</p>
            ) : (
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
                  <dt className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">Estado</dt>
                  <dd className="mt-2">
                    <HealthStateBadge state={latestHealth.health_state} />
                  </dd>
                </div>
                <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
                  <dt className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">Error recon.</dt>
                  <dd className="mt-1 text-2xl font-bold" style={{ color: healthConfig.color }}>
                    {latestHealth.recon_error != null ? latestHealth.recon_error.toFixed(3) : 'n/a'}
                  </dd>
                </div>
                <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
                  <dt className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">Umbral θ</dt>
                  <dd className="mt-1 text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                    {latestHealth.theta != null ? latestHealth.theta.toFixed(3) : 'n/a'}
                  </dd>
                </div>
              </div>
            )}
          </div>

          {/* Quick stats */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
              <p className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">Lecturas</p>
              <p className="mt-1 text-2xl font-bold text-zinc-900 dark:text-white">{lecturas.length}</p>
            </div>
            <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
              <p className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">Lecturas anómalas</p>
              <p className="mt-1 text-2xl font-bold text-zinc-900 dark:text-white">{anomalousReadings}</p>
            </div>
            <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
              <p className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">Correctivos</p>
              <p className="mt-1 text-2xl font-bold text-zinc-900 dark:text-white">{correctivos.length}</p>
            </div>
            <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
              <p className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">Calibraciones</p>
              <p className="mt-1 text-2xl font-bold text-zinc-900 dark:text-white">{calibraciones.length}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Salud (ensemble no supervisado) */}
      {activeTab === 'salud' && (
        <div className="space-y-4">
          {healthPoints.length > 0 && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-zinc-500 dark:text-zinc-400">
                Estado actual:
              </span>
              <HealthStateBadge
                state={healthPoints[healthPoints.length - 1].health_state}
              />
              <span className="text-xs text-zinc-400">
                Detección de anomalías de salud por ensemble no supervisado
                (Autoencoder + Isolation Forest).
              </span>
            </div>
          )}
          <ReconErrorChart points={healthPoints} />
        </div>
      )}

      {/* Tab: Lecturas */}
      {activeTab === 'lecturas' && (
        <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
          <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Lecturas de Sensores
          </h2>
          {lecturas.length === 0 ? (
            <p className="text-sm text-zinc-400">Sin lecturas disponibles</p>
          ) : (
            <>
              <MiniSensorChart data={sensorChartData} />
              <div className="mt-6">
                <h3 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                  Ultimas {Math.min(lecturas.length, 20)} lecturas
                </h3>
                <div className="max-h-[400px] overflow-y-auto">
                  <DataTable
                    columns={[
                      { key: 'timestamp', header: 'Timestamp', render: (l: LecturaIoT) => formatTs(l.timestamp_lectura) },
                      { key: 'so2_ppb', header: 'SO2', render: (l: LecturaIoT) => l.so2_ppb?.toFixed(1) ?? '—' },
                      { key: 'h2s_ppb', header: 'H2S', render: (l: LecturaIoT) => l.h2s_ppb?.toFixed(1) ?? '—' },
                      { key: 'reaction_temp', header: 'T.Reac', render: (l: LecturaIoT) => l.reaction_temp?.toFixed(1) ?? '—' },
                      { key: 'box_temp', header: 'T.Caja', render: (l: LecturaIoT) => l.box_temp?.toFixed(1) ?? '—' },
                      { key: 'sample_flow', header: 'Flujo', render: (l: LecturaIoT) => l.sample_flow?.toFixed(1) ?? '—' },
                      { key: 'uv_lamp', header: 'UV', render: (l: LecturaIoT) => l.uv_lamp_intensity?.toFixed(0) ?? '—' },
                    ]}
                    data={lecturas.slice(0, 20)}
                    keyExtractor={(l) => l.id}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Tab: Historial */}
      {activeTab === 'historial' && (
        <div className="space-y-8">
          {/* Correctivos */}
          <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
            <h3 className="mb-3 text-lg font-semibold text-zinc-800 dark:text-zinc-200">
              Mantenimientos Correctivos
            </h3>
            {correctivos.length === 0 ? (
              <p className="text-sm text-zinc-400">No hay registros</p>
            ) : (
              <DataTable columns={incidenciaColumns} data={correctivos} keyExtractor={(i) => i.id} />
            )}
          </div>

          {/* Calibraciones */}
          <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
            <h3 className="mb-3 text-lg font-semibold text-zinc-800 dark:text-zinc-200">
              Calibraciones
            </h3>
            {calibraciones.length === 0 ? (
              <p className="text-sm text-zinc-400">No hay registros</p>
            ) : (
              <DataTable columns={calibracionColumns} data={calibraciones} keyExtractor={(c) => c.id} />
            )}
          </div>

          {/* Incidencias de calibracion */}
          <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
            <h3 className="mb-3 text-lg font-semibold text-zinc-800 dark:text-zinc-200">
              Incidencias de Calibracion
            </h3>
            {incCalibraciones.length === 0 ? (
              <p className="text-sm text-zinc-400">No hay registros</p>
            ) : (
              <DataTable columns={incidenciaColumns} data={incCalibraciones} keyExtractor={(i) => i.id} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
