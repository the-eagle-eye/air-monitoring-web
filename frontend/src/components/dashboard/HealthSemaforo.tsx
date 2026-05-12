import type { Prediccion } from '@/types/prediccion';
import type { Incidencia } from '@/types/ops';

interface HealthSemaforoProps {
  predictions: Record<string, Prediccion>;
  totalEquipos: number;
  incidenciasAbiertas: Incidencia[];
}

function computeHealthScore(
  predictions: Record<string, Prediccion>,
  totalEquipos: number,
  incidenciasAbiertas: Incidencia[],
): number {
  if (totalEquipos === 0) return 100;

  const preds = Object.values(predictions);
  const countAlta = preds.filter((p) => p.risk_level === 'alta').length;
  const countRulCritico = preds.filter(
    (p) => p.remaining_useful_life_days < 30,
  ).length;
  const deviceIdsConIncidencia = new Set(
    incidenciasAbiertas.map((i) => i.device_id),
  );

  const pctAlta = countAlta / totalEquipos;
  const pctRulCritico = countRulCritico / totalEquipos;
  const pctConIncidencias = deviceIdsConIncidencia.size / totalEquipos;

  const score = 100 - (pctAlta * 40 + pctRulCritico * 30 + pctConIncidencias * 30);
  return Math.max(0, Math.min(100, Math.round(score)));
}

function getSemaforoConfig(score: number) {
  if (score >= 75)
    return {
      color: '#22c55e',
      bgColor: 'bg-green-50 dark:bg-green-950/40',
      borderColor: 'border-green-300 dark:border-green-800',
      label: 'Optimo',
      description: 'Los equipos operan con normalidad.',
    };
  if (score >= 50)
    return {
      color: '#eab308',
      bgColor: 'bg-yellow-50 dark:bg-yellow-950/40',
      borderColor: 'border-yellow-300 dark:border-yellow-800',
      label: 'Atencion',
      description: 'Algunos equipos requieren atencion.',
    };
  return {
    color: '#ef4444',
    bgColor: 'bg-red-50 dark:bg-red-950/40',
    borderColor: 'border-red-300 dark:border-red-800',
    label: 'Critico',
    description: 'Multiples equipos en estado critico.',
  };
}

export default function HealthSemaforo({
  predictions,
  totalEquipos,
  incidenciasAbiertas,
}: HealthSemaforoProps) {
  const score = computeHealthScore(predictions, totalEquipos, incidenciasAbiertas);
  const config = getSemaforoConfig(score);

  const preds = Object.values(predictions);
  const countAlta = preds.filter((p) => p.risk_level === 'alta').length;
  const countMedia = preds.filter((p) => p.risk_level === 'media').length;
  const countBaja = preds.filter((p) => p.risk_level === 'baja').length;

  return (
    <div
      className={`rounded-lg border p-5 ${config.bgColor} ${config.borderColor}`}
    >
      <div className="flex items-center gap-5">
        {/* Semaforo circle */}
        <div className="flex flex-col items-center gap-1">
          <div
            className="flex h-20 w-20 items-center justify-center rounded-full"
            style={{
              background: `conic-gradient(${config.color} ${score * 3.6}deg, #3f3f46 ${score * 3.6}deg)`,
            }}
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white dark:bg-zinc-900">
              <span
                className="text-xl font-bold"
                style={{ color: config.color }}
              >
                {score}
              </span>
            </div>
          </div>
        </div>

        {/* Info */}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: config.color }}
            />
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              Salud General: {config.label}
            </h2>
          </div>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            {config.description}
          </p>
          <div className="mt-3 flex gap-4 text-xs text-zinc-500 dark:text-zinc-400">
            <span>
              <span className="inline-block h-2 w-2 rounded-full bg-red-500 mr-1" />
              {countAlta} riesgo alto
            </span>
            <span>
              <span className="inline-block h-2 w-2 rounded-full bg-yellow-500 mr-1" />
              {countMedia} riesgo medio
            </span>
            <span>
              <span className="inline-block h-2 w-2 rounded-full bg-green-500 mr-1" />
              {countBaja} riesgo bajo
            </span>
            <span>
              <span className="inline-block h-2 w-2 rounded-full bg-orange-500 mr-1" />
              {new Set(incidenciasAbiertas.map((i) => i.device_id)).size} con
              incidencias
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
