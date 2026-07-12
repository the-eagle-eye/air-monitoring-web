import Link from 'next/link';
import Badge from '@/components/ui/Badge';
import StatusBadge from '@/components/ui/StatusBadge';
import type { Incidencia } from '@/types/ops';

const PRIORIDAD_VARIANT: Record<string, 'danger' | 'warning' | 'success'> = {
  alta: 'danger',
  media: 'warning',
  baja: 'success',
};

function parseUTC(ts: string): Date {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z');
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - parseUTC(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

interface IncidenciasSummaryProps {
  incidencias: Incidencia[];
}

export default function IncidenciasSummary({
  incidencias,
}: IncidenciasSummaryProps) {
  const recent = [...incidencias]
    .sort(
      (a, b) =>
        parseUTC(b.created_at).getTime() - parseUTC(a.created_at).getTime(),
    )
    .slice(0, 8);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Incidencias Correctivas Abiertas
        </h2>
        <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">
          {incidencias.length} Correctivas
        </span>
      </div>

      {recent.length === 0 ? (
        <div className="flex h-[210px] items-center justify-center text-sm text-zinc-400">
          No hay incidencias correctivas abiertas
        </div>
      ) : (
        <div className="space-y-2">
          {recent.map((inc) => (
            <Link
              key={inc.id}
              href={`/incidencias/${inc.id}`}
              className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-2 transition-colors hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
            >
              <div className="flex items-center gap-2">
                <Badge
                  label={
                    inc.prioridad.charAt(0).toUpperCase() +
                    inc.prioridad.slice(1)
                  }
                  variant={PRIORIDAD_VARIANT[inc.prioridad] ?? 'default'}
                />
                <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {inc.device_id}
                </span>
                <StatusBadge status={inc.estado} />
              </div>
              <span className="text-xs text-zinc-400">
                {timeAgo(inc.created_at)}
              </span>
            </Link>
          ))}
        </div>
      )}

      <div className="mt-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
        <Link
          href="/incidencias"
          className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          Ver todas las incidencias →
        </Link>
      </div>
    </div>
  );
}
