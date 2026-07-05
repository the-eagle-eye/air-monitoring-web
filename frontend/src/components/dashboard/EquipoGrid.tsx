import type { Equipo } from '@/types/lectura';
import type { HealthDeviceState } from '@/types/healthMonitor';
import type { Incidencia } from '@/types/ops';
import EquipoCard from './EquipoCard';

interface EquipoGridProps {
  equipos: Equipo[];
  healthStates?: Record<string, HealthDeviceState | null>;
  openIncidencias?: Incidencia[];
}

// Orden por severidad de salud del ensemble (más grave primero).
const HEALTH_PRIORITY: Record<string, number> = {
  CRITICO: 0,
  EN_RIESGO: 1,
  OBSERVADO: 2,
  SANO: 3,
  SIN_DATOS: 4,
};

export default function EquipoGrid({
  equipos,
  healthStates = {},
  openIncidencias = [],
}: EquipoGridProps) {
  // Conteo de incidencias abiertas por equipo (pendiente/en_ejecucion).
  const incidenciasPorEquipo: Record<string, number> = {};
  for (const inc of openIncidencias) {
    incidenciasPorEquipo[inc.device_id] =
      (incidenciasPorEquipo[inc.device_id] ?? 0) + 1;
  }
  if (equipos.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center text-sm text-zinc-400 dark:border-zinc-700 dark:bg-zinc-900">
        No hay equipos registrados
      </div>
    );
  }

  const sorted = [...equipos].sort((a, b) => {
    const sa = healthStates[a.device_id]?.health_state;
    const sb = healthStates[b.device_id]?.health_state;
    const pa = sa ? (HEALTH_PRIORITY[sa] ?? 5) : 5;
    const pb = sb ? (HEALTH_PRIORITY[sb] ?? 5) : 5;
    return pa - pb;
  });

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        Estado de Equipos
      </h2>
      <div className="flex items-stretch gap-4 overflow-x-auto pb-2">
        {sorted.map((equipo) => (
          <div key={equipo.device_id} className="min-w-[280px] flex-shrink-0 self-stretch">
            <EquipoCard
              equipo={equipo}
              health={healthStates[equipo.device_id] ?? null}
              incidenciasAbiertas={incidenciasPorEquipo[equipo.device_id] ?? 0}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
