import Link from 'next/link';
import type { HealthDeviceState } from '@/types/healthMonitor';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';
import type { Incidencia } from '@/types/ops';

interface EquiposAtencionProps {
  states: Record<string, HealthDeviceState | null>;
  // Incidencias correctivas abiertas (pendiente + en_ejecucion) por equipo.
  openIncidencias?: Incidencia[];
}

const ATTENTION_ORDER: Record<string, number> = {
  CRITICO: 3,
  EN_RIESGO: 2,
  OBSERVADO: 1,
};

// Un equipo con incidencia abierta pero salud ya recuperada se ordena por debajo
// de las anomalías activas, pero por encima de nada.
const SEGUIMIENTO_ORDER = 0.5;

// Color neutro para "En seguimiento" (salud SANO pero incidencia abierta).
const SEGUIMIENTO_COLOR = '#3b82f6'; // blue-500

interface AtencionItem {
  device_id: string;
  order: number;
  label: string;
  color: string;
  updated_at: string | null;
  enSeguimiento: boolean;
}

function parseUTC(ts: string): Date {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z');
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - parseUTC(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

// Equipos que requieren atención según el ensemble (observado/en riesgo/crítico)
// O que tienen una incidencia correctiva abierta (aunque su salud haya vuelto a
// SANO): estos siguen visibles como "En seguimiento" para que el coordinador no
// pierda de vista un equipo con problema aún sin cerrar. Reemplaza a "Alertas
// Recientes" (modelo RF), retirada con el RF.
export default function EquiposAtencion({ states, openIncidencias = [] }: EquiposAtencionProps) {
  // Equipos con incidencia correctiva abierta (dedup por device_id).
  const conIncidencia = new Set(openIncidencias.map((i) => i.device_id));

  // Unión de device_ids: los que tienen estado de salud + los que tienen incidencia.
  const deviceIds = new Set<string>([
    ...Object.keys(states),
    ...conIncidencia,
  ]);

  const items: AtencionItem[] = [];
  for (const id of deviceIds) {
    const s = states[id] ?? null;
    const anomalo = s != null && ATTENTION_ORDER[s.health_state] != null;
    const abierta = conIncidencia.has(id);

    if (anomalo && s) {
      // Anomalía de salud activa: se muestra su estado (independiente de incidencia).
      const cfg = HEALTH_STATE_CONFIG[s.health_state];
      items.push({
        device_id: id,
        order: ATTENTION_ORDER[s.health_state],
        label: cfg.label,
        color: cfg.color,
        updated_at: s.updated_at,
        enSeguimiento: false,
      });
    } else if (abierta) {
      // Salud SANO/sin dato pero incidencia abierta -> "En seguimiento".
      items.push({
        device_id: id,
        order: SEGUIMIENTO_ORDER,
        label: 'En seguimiento',
        color: SEGUIMIENTO_COLOR,
        updated_at: s?.updated_at ?? null,
        enSeguimiento: true,
      });
    }
  }

  const atencion = items.sort((a, b) => b.order - a.order);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        Equipos que requieren atención
      </h2>

      {atencion.length === 0 ? (
        <div className="flex h-[210px] items-center justify-center text-sm text-zinc-400">
          Ningún equipo con anomalía ni incidencia abierta.
        </div>
      ) : (
        <div className="space-y-2">
          {atencion.map((item) => (
            <Link
              key={item.device_id}
              href={`/equipos/${item.device_id}`}
              className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-2 transition-colors hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
            >
              <div className="flex items-center gap-2">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {item.device_id}
                </span>
                <span className="text-xs font-medium" style={{ color: item.color }}>
                  {item.label}
                </span>
                {item.enSeguimiento && (
                  <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
                    incidencia abierta
                  </span>
                )}
              </div>
              {item.updated_at && (
                <span className="text-xs text-zinc-400">
                  {timeAgo(item.updated_at)}
                </span>
              )}
            </Link>
          ))}
        </div>
      )}

      <div className="mt-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
        <Link
          href="/incidencias"
          className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          Ver incidencias →
        </Link>
      </div>
    </div>
  );
}
