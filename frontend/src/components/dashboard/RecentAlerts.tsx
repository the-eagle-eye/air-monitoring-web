import Link from 'next/link';
import RiskBadge from '@/components/ui/RiskBadge';
import type { Alerta } from '@/types/prediccion';

interface RecentAlertsProps {
  alertas: Alerta[];
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

export default function RecentAlerts({ alertas }: RecentAlertsProps) {
  const recent = alertas.slice(0, 10);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        Alertas Recientes
      </h2>
      {recent.length === 0 ? (
        <div className="flex h-[210px] items-center justify-center text-sm text-zinc-400">
          Sin alertas recientes
        </div>
      ) : (
        <div className="space-y-2">
          {recent.map((alerta) => (
            <div
              key={alerta.id}
              className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-2 dark:border-zinc-800"
            >
              <div className="flex items-center gap-2">
                <RiskBadge level={alerta.nivel_riesgo} />
                <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {alerta.device_id}
                </span>
                {alerta.descripcion && (
                  <span className="max-w-[150px] truncate text-xs text-zinc-500 dark:text-zinc-400">
                    {alerta.descripcion}
                  </span>
                )}
              </div>
              <span className="text-xs text-zinc-400">
                {timeAgo(alerta.created_at)}
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="mt-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
        <Link
          href="/alertas"
          className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          Ver todas las alertas →
        </Link>
      </div>
    </div>
  );
}
