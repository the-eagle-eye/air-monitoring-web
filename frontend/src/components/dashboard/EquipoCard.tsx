import Link from 'next/link';
import type { Equipo } from '@/types/lectura';
import type { Prediccion } from '@/types/prediccion';
import RiskBadge from '@/components/ui/RiskBadge';

interface EquipoCardProps {
  equipo: Equipo;
  prediction: Prediccion | null;
}

const ESTADO_CONFIG: Record<string, { color: string; label: string }> = {
  activo: { color: 'text-green-600', label: 'Activo' },
  en_revision: { color: 'text-yellow-600', label: 'En revision' },
  fuera_servicio: { color: 'text-red-600', label: 'Fuera de servicio' },
};

const BORDER_COLORS: Record<string, string> = {
  alta: 'border-l-red-500',
  media: 'border-l-yellow-500',
  baja: 'border-l-green-500',
};

function SensorIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="8" y="6" width="32" height="36" rx="4" stroke="currentColor" strokeWidth="2" fill="none" />
      <rect x="14" y="12" width="20" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <line x1="18" y1="16" x2="18" y2="22" stroke="currentColor" strokeWidth="1.5" />
      <line x1="22" y1="14" x2="22" y2="22" stroke="currentColor" strokeWidth="1.5" />
      <line x1="26" y1="17" x2="26" y2="22" stroke="currentColor" strokeWidth="1.5" />
      <line x1="30" y1="15" x2="30" y2="22" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="17" cy="32" r="2" fill="currentColor" />
      <circle cx="24" cy="32" r="2" fill="currentColor" />
      <circle cx="31" cy="32" r="2" fill="currentColor" />
      <rect x="14" y="38" width="8" height="2" rx="1" fill="currentColor" />
    </svg>
  );
}

export default function EquipoCard({ equipo, prediction }: EquipoCardProps) {
  const estadoInfo = ESTADO_CONFIG[equipo.estado] ?? ESTADO_CONFIG.activo;
  const riskLevel = prediction?.risk_level ?? 'baja';
  const borderColor = BORDER_COLORS[riskLevel] ?? BORDER_COLORS.baja;

  const failurePercent = prediction
    ? Math.round(prediction.failure_probability * 100)
    : 0;

  return (
    <Link
      href={`/equipos/${equipo.device_id}`}
      className={`flex h-full flex-col rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900 border-l-4 ${borderColor} p-4 transition-shadow hover:shadow-md`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 text-zinc-400 dark:text-zinc-500">
          <SensorIcon className="h-12 w-12" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              {equipo.device_id}
            </h3>
            {prediction && <RiskBadge level={prediction.risk_level} />}
          </div>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            {equipo.nombre ?? equipo.tipo ?? 'Equipo de medicion'}
          </p>
          <div className="mt-1 flex items-center gap-1.5">
            <span className={`text-xs font-medium ${estadoInfo.color}`}>
              {estadoInfo.label}
            </span>
          </div>
        </div>
      </div>

      {prediction && (
        <div className="mt-3 space-y-2 border-t border-zinc-100 pt-3 dark:border-zinc-800">
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-500 dark:text-zinc-400">
              Prob. falla
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              {failurePercent}%
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-zinc-100 dark:bg-zinc-800">
            <div
              className={`h-1.5 rounded-full ${
                failurePercent >= 70
                  ? 'bg-red-500'
                  : failurePercent >= 40
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(failurePercent, 100)}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-500 dark:text-zinc-400">
              Vida util restante
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              {prediction.remaining_useful_life_days} dias
            </span>
          </div>
        </div>
      )}

      {!prediction && (
        <div className="mt-3 flex flex-1 items-center border-t border-zinc-100 pt-3 dark:border-zinc-800">
          <p className="text-xs text-zinc-400">Sin predicciones disponibles</p>
        </div>
      )}
    </Link>
  );
}
