import type { KpiData } from '@/types/dashboard';

interface KpiCardsProps {
  data: KpiData;
}

const cards = [
  {
    key: 'totalEquipos' as const,
    label: 'Total Equipos',
    accent: 'text-blue-600',
    bg: 'bg-blue-50 dark:bg-blue-950',
    format: (v: number) => String(v),
  },
  {
    key: 'alertasAltas' as const,
    label: 'Alertas Altas',
    accent: 'text-red-600',
    bg: 'bg-red-50 dark:bg-red-950',
    format: (v: number) => String(v),
  },
  {
    key: 'rulPromedio' as const,
    label: 'RUL Promedio',
    accent: 'text-yellow-600',
    bg: 'bg-yellow-50 dark:bg-yellow-950',
    format: (v: number) => `${v} dias`,
  },
  {
    key: 'prediccionesRecientes' as const,
    label: 'Predicciones',
    accent: 'text-green-600',
    bg: 'bg-green-50 dark:bg-green-950',
    format: (v: number) => String(v),
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
            {card.format(data[card.key])}
          </p>
        </div>
      ))}
    </div>
  );
}
