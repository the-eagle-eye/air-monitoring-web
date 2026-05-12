'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { usePolling } from '@/hooks/usePolling';
import { fetchIncidencias, fetchRepuestos } from '@/lib/api/ops';
import { fetchEquipos } from '@/lib/api/lecturas';
import { fetchPredicciones } from '@/lib/api/predicciones';
import Badge from '@/components/ui/Badge';
import StatusBadge from '@/components/ui/StatusBadge';
import RiskBadge from '@/components/ui/RiskBadge';
import type { Incidencia, Repuesto } from '@/types/ops';
import type { Equipo } from '@/types/lectura';
import type { Prediccion } from '@/types/prediccion';

const PRIORIDAD_VARIANT: Record<string, 'danger' | 'warning' | 'success'> = {
  alta: 'danger',
  media: 'warning',
  baja: 'success',
};

function parseUTC(ts: string): Date {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z');
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - parseUTC(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

interface TecnicoKpis {
  pendientes: number;
  enEjecucion: number;
  finalizadasMes: number;
  equiposActivos: number;
}

export default function DashboardTecnicoPage() {
  const [pendientes, setPendientes] = useState<Incidencia[]>([]);
  const [enEjecucion, setEnEjecucion] = useState<Incidencia[]>([]);
  const [finalizadas, setFinalizadas] = useState<Incidencia[]>([]);
  const [equipos, setEquipos] = useState<Equipo[]>([]);
  const [predictions, setPredictions] = useState<Record<string, Prediccion>>({});
  const [repuestos, setRepuestos] = useState<Repuesto[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadData = useCallback((silent = false) => {
    if (!silent) setLoading(true);

    Promise.all([
      fetchIncidencias({ estado: 'pendiente', page_size: 50 }),
      fetchIncidencias({ estado: 'en_ejecucion', page_size: 50 }),
      fetchIncidencias({ estado: 'finalizado', page_size: 50 }),
      fetchEquipos(),
      fetchRepuestos(),
    ])
      .then(async ([pend, ejec, fin, eqs, reps]) => {
        setPendientes(pend.items);
        setEnEjecucion(ejec.items);
        setFinalizadas(fin.items);
        setEquipos(eqs);
        setRepuestos(reps);
        setLastUpdated(new Date());

        // Fetch predictions for related equipment
        const activeDeviceIds = new Set([
          ...pend.items.map((i) => i.device_id),
          ...ejec.items.map((i) => i.device_id),
        ]);
        const predResults = await Promise.allSettled(
          [...activeDeviceIds].map((did) => fetchPredicciones(did, 1, 1)),
        );
        const preds: Record<string, Prediccion> = {};
        [...activeDeviceIds].forEach((did, idx) => {
          const r = predResults[idx];
          if (r.status === 'fulfilled' && r.value.items.length > 0) {
            preds[did] = r.value.items[0];
          }
        });
        setPredictions(preds);
      })
      .catch(() => {})
      .finally(() => { if (!silent) setLoading(false); });
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  usePolling(() => loadData(true), 30_000);

  const activeIncidencias = [...pendientes, ...enEjecucion].sort(
    (a, b) => parseUTC(b.created_at).getTime() - parseUTC(a.created_at).getTime(),
  );

  // Finalizadas this month
  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const finalizadasMes = finalizadas.filter(
    (i) => parseUTC(i.created_at) >= monthStart,
  );

  // Unique active device_ids
  const activeDeviceIds = [...new Set(activeIncidencias.map((i) => i.device_id))];
  const relatedEquipos = equipos.filter((eq) => activeDeviceIds.includes(eq.device_id));

  // Repuestos used in finalized mantenimientos
  const repuestosUsados = finalizadas
    .filter((i) => i.mantenimiento_correctivo?.repuestos?.length)
    .flatMap((i) => i.mantenimiento_correctivo!.repuestos)
    .slice(0, 10);

  const kpis: TecnicoKpis = {
    pendientes: pendientes.length,
    enEjecucion: enEjecucion.length,
    finalizadasMes: finalizadasMes.length,
    equiposActivos: activeDeviceIds.length,
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="py-12 text-center text-zinc-400">Cargando dashboard...</div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Mi Panel de Trabajo
        </h1>
        {lastUpdated && (
          <span className="text-xs text-zinc-400">
            Actualizado: {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard label="Pendientes" value={kpis.pendientes} color="text-amber-600" bg="bg-amber-50 dark:bg-amber-900/20" />
        <KpiCard label="En Ejecucion" value={kpis.enEjecucion} color="text-blue-600" bg="bg-blue-50 dark:bg-blue-900/20" />
        <KpiCard label="Finalizadas (mes)" value={kpis.finalizadasMes} color="text-green-600" bg="bg-green-50 dark:bg-green-900/20" />
        <KpiCard label="Equipos Activos" value={kpis.equiposActivos} color="text-zinc-600" bg="bg-zinc-50 dark:bg-zinc-800" />
      </div>

      {/* Mis Incidencias Activas */}
      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Mis Incidencias Activas
          </h2>
          <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">
            {activeIncidencias.length} activas
          </span>
        </div>

        {activeIncidencias.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-zinc-400">
            No tienes incidencias activas asignadas
          </div>
        ) : (
          <div className="space-y-2">
            {activeIncidencias.map((inc) => (
              <Link
                key={inc.id}
                href={`/incidencias/${inc.id}`}
                className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-2.5 transition-colors hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
              >
                <div className="flex items-center gap-2">
                  <Badge
                    label={inc.prioridad.charAt(0).toUpperCase() + inc.prioridad.slice(1)}
                    variant={PRIORIDAD_VARIANT[inc.prioridad] ?? 'default'}
                  />
                  <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                    {inc.device_id}
                  </span>
                  <StatusBadge status={inc.estado} />
                  {inc.descripcion && (
                    <span className="hidden text-xs text-zinc-400 sm:inline">
                      {inc.descripcion.length > 50
                        ? inc.descripcion.slice(0, 50) + '...'
                        : inc.descripcion}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-400">{timeAgo(inc.created_at)}</span>
                  <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                    Gestionar
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}

        <div className="mt-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
          <Link
            href="/incidencias"
            className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            Ver todas mis incidencias →
          </Link>
        </div>
      </div>

      {/* Equipos Relacionados + Repuestos */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Equipos */}
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
          <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Equipos con Incidencias
          </h2>
          {relatedEquipos.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-sm text-zinc-400">
              Sin equipos con incidencias activas
            </div>
          ) : (
            <div className="space-y-3">
              {relatedEquipos.map((eq) => {
                const pred = predictions[eq.device_id];
                const incCount = activeIncidencias.filter(
                  (i) => i.device_id === eq.device_id,
                ).length;
                return (
                  <Link
                    key={eq.device_id}
                    href={`/equipos/${eq.device_id}`}
                    className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-3 transition-colors hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                          {eq.device_id}
                        </span>
                        {pred && <RiskBadge level={pred.risk_level} />}
                      </div>
                      <p className="mt-0.5 text-xs text-zinc-500">
                        {eq.nombre ?? eq.tipo ?? 'Equipo de medicion'}
                      </p>
                    </div>
                    <div className="text-right">
                      {pred ? (
                        <>
                          <div className="text-xs text-zinc-500">
                            RUL: <span className="font-semibold text-zinc-900 dark:text-zinc-100">{pred.remaining_useful_life_days}d</span>
                          </div>
                          <div className="text-xs text-zinc-500">
                            Falla: <span className="font-semibold text-zinc-900 dark:text-zinc-100">{Math.round(pred.failure_probability * 100)}%</span>
                          </div>
                        </>
                      ) : (
                        <span className="text-xs text-zinc-400">Sin prediccion</span>
                      )}
                      <div className="mt-1 text-xs text-zinc-400">
                        {incCount} incidencia{incCount > 1 ? 's' : ''}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Repuestos */}
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              Repuestos Disponibles
            </h2>
            <span className="text-xs text-zinc-400">
              {repuestos.length} activos
            </span>
          </div>

          {repuestosUsados.length > 0 && (
            <div className="mb-4">
              <h3 className="mb-2 text-xs font-medium uppercase text-zinc-500">
                Usados recientemente
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {repuestosUsados.map((r, idx) => (
                  <span
                    key={`${r.id}-${idx}`}
                    className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                  >
                    {r.nombre}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Top categories */}
          <div className="space-y-2">
            {Object.entries(
              repuestos.reduce<Record<string, number>>((acc, r) => {
                acc[r.categoria] = (acc[r.categoria] ?? 0) + 1;
                return acc;
              }, {}),
            )
              .sort((a, b) => b[1] - a[1])
              .slice(0, 6)
              .map(([cat, count]) => (
                <div
                  key={cat}
                  className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-2 dark:border-zinc-800"
                >
                  <span className="text-sm text-zinc-700 dark:text-zinc-300">{cat}</span>
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                    {count}
                  </span>
                </div>
              ))}
          </div>

          <div className="mt-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
            <Link
              href="/repuestos"
              className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              Gestionar repuestos →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  color,
  bg,
}: {
  label: string;
  value: number;
  color: string;
  bg: string;
}) {
  return (
    <div className={`rounded-lg border border-zinc-200 p-4 dark:border-zinc-700 ${bg}`}>
      <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}
