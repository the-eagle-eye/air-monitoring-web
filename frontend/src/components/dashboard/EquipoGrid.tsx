import type { Equipo } from '@/types/lectura';
import type { Prediccion } from '@/types/prediccion';
import EquipoCard from './EquipoCard';

interface EquipoGridProps {
  equipos: Equipo[];
  predictions: Record<string, Prediccion>;
}

export default function EquipoGrid({ equipos, predictions }: EquipoGridProps) {
  if (equipos.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center text-sm text-zinc-400 dark:border-zinc-700 dark:bg-zinc-900">
        No hay equipos registrados
      </div>
    );
  }

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        Estado de Equipos
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {equipos.map((equipo) => (
          <EquipoCard
            key={equipo.device_id}
            equipo={equipo}
            prediction={predictions[equipo.device_id] ?? null}
          />
        ))}
      </div>
    </div>
  );
}
