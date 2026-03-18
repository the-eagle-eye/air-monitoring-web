import type { Equipo } from '@/types/lectura';
import type { Prediccion } from '@/types/prediccion';
import EquipoCard from './EquipoCard';

interface EquipoGridProps {
  equipos: Equipo[];
  predictions: Record<string, Prediccion>;
}

const RISK_PRIORITY: Record<string, number> = {
  alta: 0,
  media: 1,
  baja: 2,
};

export default function EquipoGrid({ equipos, predictions }: EquipoGridProps) {
  if (equipos.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center text-sm text-zinc-400 dark:border-zinc-700 dark:bg-zinc-900">
        No hay equipos registrados
      </div>
    );
  }

  const sorted = [...equipos].sort((a, b) => {
    const riskA = predictions[a.device_id]?.risk_level;
    const riskB = predictions[b.device_id]?.risk_level;
    const priorityA = riskA ? (RISK_PRIORITY[riskA] ?? 3) : 3;
    const priorityB = riskB ? (RISK_PRIORITY[riskB] ?? 3) : 3;
    return priorityA - priorityB;
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
              prediction={predictions[equipo.device_id] ?? null}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
