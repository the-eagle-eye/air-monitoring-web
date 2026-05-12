import Link from 'next/link';
import type { CalibracionOps } from '@/types/ops';

function parseUTC(ts: string): Date {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z');
}

interface ProximasCalibracionesProps {
  calibraciones: CalibracionOps[];
}

export default function ProximasCalibraciones({ calibraciones }: ProximasCalibracionesProps) {
  const recent = calibraciones.slice(0, 8);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Proximas Calibraciones
        </h2>
        <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
          {calibraciones.length} pendientes
        </span>
      </div>

      {recent.length === 0 ? (
        <div className="flex h-[210px] items-center justify-center text-sm text-zinc-400">
          No hay calibraciones pendientes
        </div>
      ) : (
        <div className="space-y-2">
          {recent.map((cal) => (
            <Link
              key={cal.id}
              href={`/calibraciones/${cal.id}`}
              className="flex items-center justify-between rounded-md border border-zinc-100 px-3 py-2 transition-colors hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {cal.device_id}
                </span>
                <span className="max-w-[200px] truncate text-xs text-zinc-500 dark:text-zinc-400">
                  {cal.nota ?? '—'}
                </span>
              </div>
              <span className="text-xs text-zinc-400">
                {parseUTC(cal.created_at).toLocaleDateString()}
              </span>
            </Link>
          ))}
        </div>
      )}

      <div className="mt-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
        <Link
          href="/calibraciones"
          className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          Ver todas las calibraciones →
        </Link>
      </div>
    </div>
  );
}
