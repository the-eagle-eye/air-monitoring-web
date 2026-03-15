import RiskBadge from '@/components/ui/RiskBadge';
import type { Prediccion } from '@/types/prediccion';

interface PrediccionCardProps {
  prediccion: Prediccion;
}

export default function PrediccionCard({ prediccion }: PrediccionCardProps) {
  const probPercent = (prediccion.failure_probability * 100).toFixed(1);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-zinc-900 dark:text-white">
          {prediccion.device_id}
        </h3>
        <RiskBadge level={prediccion.risk_level} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Probabilidad de Falla
          </p>
          <p className="text-xl font-bold text-zinc-900 dark:text-white">
            {probPercent}%
          </p>
        </div>
        <div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Vida Util Restante
          </p>
          <p className="text-xl font-bold text-zinc-900 dark:text-white">
            {prediccion.remaining_useful_life_days} dias
          </p>
        </div>
      </div>

      <div className="mt-3 border-t border-zinc-100 pt-2 dark:border-zinc-700">
        <p className="text-xs text-zinc-400">
          Modelo: {prediccion.model_version} |{' '}
          {new Date(prediccion.prediction_timestamp).toLocaleString()}
        </p>
      </div>
    </div>
  );
}
