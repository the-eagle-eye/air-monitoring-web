import Link from 'next/link';
import type { HealthDeviceState } from '@/types/healthMonitor';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';

interface EquiposAtencionProps {
  states: Record<string, HealthDeviceState | null>;
}

const ATTENTION_ORDER: Record<string, number> = {
  CRITICO: 3,
  EN_RIESGO: 2,
  OBSERVADO: 1,
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
  return `hace ${Math.floor(hours / 24)}d`;
}

// Equipos que requieren atención según el ensemble (observado/en riesgo/crítico).
// Reemplaza a "Alertas Recientes" (modelo RF), retirada con el RF.
export default function EquiposAtencion({ states }: EquiposAtencionProps) {
  const atencion = Object.values(states)
    .filter(
      (s): s is HealthDeviceState =>
        s !== null && ATTENTION_ORDER[s.health_state] != null,
    )
    .sort(
      (a, b) => ATTENTION_ORDER[b.health_state] - ATTENTION_ORDER[a.health_state],
    );

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        Equipos que requieren atención
      </h2>

      {atencion.length === 0 ? (
        <div className="flex h-[210px] items-center justify-center text-sm text-zinc-400">
          Ningún equipo con anomalía de salud.
        </div>
      ) : (
        <div className="space-y-2">
          {atencion.map((s) => {
            const cfg = HEALTH_STATE_CONFIG[s.health_state];
            return (
              <Link
                key={s.device_id}
                href={`/equipos/${s.device_id}`}
                className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-2 transition-colors hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: cfg.color }}
                  />
                  <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                    {s.device_id}
                  </span>
                  <span
                    className="text-xs font-medium"
                    style={{ color: cfg.color }}
                  >
                    {cfg.label}
                  </span>
                </div>
                <span className="text-xs text-zinc-400">
                  {timeAgo(s.updated_at)}
                </span>
              </Link>
            );
          })}
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
