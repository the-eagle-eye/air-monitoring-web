import Link from 'next/link';
import type { Equipo } from '@/types/lectura';
import type { HealthDeviceState } from '@/types/healthMonitor';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';
import HealthStateBadge from '@/components/dashboard/HealthStateBadge';

interface EquipoCardProps {
  equipo: Equipo;
  health?: HealthDeviceState | null;
  incidenciasAbiertas?: number;
}

const ESTADO_CONFIG: Record<string, { color: string; label: string }> = {
  activo: { color: 'text-green-600', label: 'Activo' },
  en_revision: { color: 'text-yellow-600', label: 'En revision' },
  fuera_servicio: { color: 'text-red-600', label: 'Fuera de servicio' },
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

// Acción sugerida por estado de salud (poc-dashboard §1).
const ACCION_SUGERIDA: Record<string, string> = {
  SANO: 'Operación normal.',
  OBSERVADO: 'Vigilar en la próxima ronda.',
  EN_RIESGO: 'Planificar intervención esta semana.',
  CRITICO: 'Despacho inmediato al sitio.',
  SIN_DATOS: 'Revisar PC / energía / transmisión.',
};

// Borde izquierdo por severidad de salud del ensemble.
const HEALTH_BORDER: Record<string, string> = {
  SANO: 'border-l-green-500',
  OBSERVADO: 'border-l-yellow-500',
  EN_RIESGO: 'border-l-orange-500',
  CRITICO: 'border-l-red-500',
  SIN_DATOS: 'border-l-zinc-500',
};

export default function EquipoCard({
  equipo,
  health,
  incidenciasAbiertas = 0,
}: EquipoCardProps) {
  const estadoInfo = ESTADO_CONFIG[equipo.estado] ?? ESTADO_CONFIG.activo;
  const state = health?.health_state ?? null;
  // Borde por severidad de salud del ensemble (gris si aún no hay estado).
  const borderColor = state ? HEALTH_BORDER[state] : 'border-l-zinc-300 dark:border-l-zinc-700';

  const hsp = health?.hours_since_prev;

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
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              {equipo.device_id}
            </h3>
            {state && <HealthStateBadge state={state} size="sm" />}
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

      {state ? (
        <div className="mt-3 space-y-1.5 border-t border-zinc-100 pt-3 dark:border-zinc-800">
          {state !== 'SIN_DATOS' && hsp != null && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-500 dark:text-zinc-400">
                Operando sin corte
              </span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                {hsp < 1 ? `${Math.round(hsp * 60)} min` : `${hsp.toFixed(1)} h`}
              </span>
            </div>
          )}
          <div className="flex items-start justify-between gap-2 text-xs">
            <span className="text-zinc-500 dark:text-zinc-400">Acción</span>
            <span
              className="text-right font-medium"
              style={{ color: HEALTH_STATE_CONFIG[state].color }}
            >
              {ACCION_SUGERIDA[state]}
            </span>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex flex-1 items-center border-t border-zinc-100 pt-3 dark:border-zinc-800">
          <p className="text-xs text-zinc-400">Sin datos de salud aún</p>
        </div>
      )}

      {incidenciasAbiertas > 0 && (
        <div className="mt-2 flex items-center gap-1.5 rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
          <span aria-hidden>⚠</span>
          {incidenciasAbiertas === 1
            ? '1 incidencia abierta'
            : `${incidenciasAbiertas} incidencias abiertas`}
        </div>
      )}
    </Link>
  );
}
