import type { HealthDeviceState, HealthState } from '@/types/healthMonitor';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';

interface SaludPredictivaSemaforoProps {
  // estado del ensemble por device_id (null = sin estado aún)
  states: Record<string, HealthDeviceState | null>;
}

// Pesos de penalización por estado (poc-dashboard §2.4). SIN_DATOS se excluye
// del cómputo: sin transmisión no hay "salud medida".
const PENALTY: Record<HealthState, number> = {
  SANO: 0,
  OBSERVADO: 15,
  EN_RIESGO: 25,
  CRITICO: 40,
  SIN_DATOS: 0, // no penaliza (se excluye del denominador)
};

function computeScore(evaluables: HealthState[]): number {
  if (evaluables.length === 0) return 100;
  const totalPenalty = evaluables.reduce((acc, s) => acc + PENALTY[s], 0);
  return Math.max(0, Math.min(100, Math.round(100 - totalPenalty / evaluables.length)));
}

function getConfig(score: number, countCritico: number) {
  if (countCritico >= 1 || score < 50) {
    return {
      color: '#ef4444',
      bg: 'bg-red-50 dark:bg-red-950/40',
      border: 'border-red-300 dark:border-red-800',
      label: 'Crítico',
      desc: 'Uno o más equipos con anomalía de salud crítica.',
    };
  }
  if (score < 75) {
    return {
      color: '#eab308',
      bg: 'bg-yellow-50 dark:bg-yellow-950/40',
      border: 'border-yellow-300 dark:border-yellow-800',
      label: 'Atención',
      desc: 'Algunos equipos muestran desviación de salud.',
    };
  }
  return {
    color: '#22c55e',
    bg: 'bg-green-50 dark:bg-green-950/40',
    border: 'border-green-300 dark:border-green-800',
    label: 'Óptimo',
    desc: 'Salud de los equipos dentro de lo normal.',
  };
}

export default function SaludPredictivaSemaforo({
  states,
}: SaludPredictivaSemaforoProps) {
  const all = Object.values(states).filter(
    (s): s is HealthDeviceState => s !== null,
  );
  // SIN_DATOS excluido del cómputo del score (§2.4/§2.5)
  const evaluables = all
    .map((s) => s.health_state)
    .filter((s) => s !== 'SIN_DATOS');

  const score = computeScore(evaluables);
  const count = (st: HealthState) =>
    all.filter((s) => s.health_state === st).length;
  const config = getConfig(score, count('CRITICO'));

  return (
    <div className={`rounded-lg border p-5 ${config.bg} ${config.border}`}>
      <div className="flex items-center gap-5">
        <div className="flex flex-col items-center gap-1">
          <div
            className="flex h-20 w-20 items-center justify-center rounded-full"
            style={{
              background: `conic-gradient(${config.color} ${score * 3.6}deg, #3f3f46 ${score * 3.6}deg)`,
            }}
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white dark:bg-zinc-900">
              <span className="text-xl font-bold" style={{ color: config.color }}>
                {score}
              </span>
            </div>
          </div>
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: config.color }}
            />
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              Salud Predictiva: {config.label}
            </h2>
          </div>
          <p className="mt-0.5 text-xs text-zinc-400 dark:text-zinc-500">
            Detección de anomalías del sensor por IA (Autoencoder + Isolation Forest)
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            {config.desc}
          </p>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-500 dark:text-zinc-400">
            {(['OBSERVADO', 'EN_RIESGO', 'CRITICO', 'SANO', 'SIN_DATOS'] as HealthState[]).map(
              (st) => (
                <span key={st}>
                  <span
                    className="mr-1 inline-block h-2 w-2 rounded-full"
                    style={{ backgroundColor: HEALTH_STATE_CONFIG[st].color }}
                  />
                  {count(st)} {HEALTH_STATE_CONFIG[st].label.toLowerCase()}
                </span>
              ),
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
