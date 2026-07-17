import type { TrainingStateItem } from '@/types/healthMonitor';

interface EquiposEnWarmupProps {
  items: TrainingStateItem[];
}

// C11 auto-training onboarding: muestra estaciones que aún no tienen θ propio,
// con progreso (readings_valid_count / target) y ETA en días.
// Ver docs/spec-auto-training-onboarding.md §8.
const STATE_LABEL: Record<string, { label: string; color: string }> = {
  nueva: { label: 'Registrando', color: 'bg-zinc-500' },
  recolectando: { label: 'Recolectando', color: 'bg-blue-500' },
  entrenando: { label: 'Entrenando', color: 'bg-purple-500' },
  error: { label: 'Error', color: 'bg-red-500' },
};

function formatEta(etaDays: number | null): string {
  if (etaDays == null) return '—';
  if (etaDays < 1) {
    const hours = Math.max(1, Math.round(etaDays * 24));
    return `~${hours} h`;
  }
  return `~${etaDays.toFixed(1)} d`;
}

export default function EquiposEnWarmup({ items }: EquiposEnWarmupProps) {
  if (items.length === 0) return null;

  return (
    <div className="rounded-lg border border-blue-300 bg-blue-50 p-5 dark:border-blue-800 dark:bg-blue-950/30">
      <div className="flex items-center gap-2">
        <span className="inline-block h-3 w-3 rounded-full bg-blue-500" />
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Equipos en warm-up ({items.length})
        </h2>
      </div>
      <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
        Recolectando lecturas para entrenar el modelo por estación. Se activa el
        monitoreo automáticamente al completar el umbral.
      </p>

      <ul className="mt-3 space-y-3">
        {items.map((it) => {
          const cfg = STATE_LABEL[it.state] ?? {
            label: it.state,
            color: 'bg-zinc-500',
          };
          const pct = Math.min(
            100,
            Math.round(
              (it.readings_valid_count / Math.max(1, it.target)) * 100,
            ),
          );
          return (
            <li key={it.device_id} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span className="font-medium text-zinc-800 dark:text-zinc-200">
                    {it.device_id}
                  </span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium text-white ${cfg.color}`}
                  >
                    {cfg.label}
                  </span>
                  {it.state === 'entrenando' && (
                    <span
                      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-purple-300 border-t-transparent"
                      aria-label="entrenando"
                    />
                  )}
                </span>
                <span className="text-zinc-600 dark:text-zinc-400">
                  {it.readings_valid_count} / {it.target}
                  {it.state === 'recolectando' && (
                    <span className="ml-2 text-zinc-500">
                      · ETA {formatEta(it.eta_days)}
                    </span>
                  )}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
                <div
                  className={`h-full ${cfg.color}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              {it.state === 'error' && it.last_error && (
                <p
                  className="text-xs text-red-700 dark:text-red-400"
                  title={it.last_error}
                >
                  {it.last_error.length > 120
                    ? `${it.last_error.slice(0, 120)}…`
                    : it.last_error}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
