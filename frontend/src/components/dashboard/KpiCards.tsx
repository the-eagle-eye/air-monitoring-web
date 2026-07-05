import type { KpiData } from '@/types/dashboard';

interface KpiCardsProps {
  data: KpiData;
}

// KPIs del modelo ensemble (AE+IF+AND). Las antiguas KPIs RF (Alertas Activas,
// RUL Promedio, Predicciones) se retiraron al migrar del Random Forest.
const cards = [
  {
    key: 'totalEquipos' as const,
    label: 'Equipos monitoreados',
    accent: 'text-blue-600',
    bg: 'bg-blue-50 dark:bg-blue-950',
  },
  {
    key: 'anomalias24h' as const,
    label: 'Equipos con anomalía',
    accent: 'text-orange-600',
    bg: 'bg-orange-50 dark:bg-orange-950',
  },
  {
    key: 'incidenciasAbiertas' as const,
    label: 'Incidencias abiertas',
    accent: 'text-red-600',
    bg: 'bg-red-50 dark:bg-red-950',
  },
  {
    key: 'sinTransmision' as const,
    label: 'Sin transmisión',
    accent: 'text-zinc-500',
    bg: 'bg-zinc-100 dark:bg-zinc-900',
  },
];

export default function KpiCards({ data }: KpiCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.key}
          className={`rounded-lg border border-zinc-200 p-4 dark:border-zinc-700 ${card.bg}`}
        >
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
            {card.label}
          </p>
          <p className={`mt-1 text-2xl font-bold ${card.accent}`}>
            {data[card.key]}
          </p>
        </div>
      ))}
    </div>
  );
}
