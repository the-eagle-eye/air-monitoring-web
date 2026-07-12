'use client';

import type { HealthReadingPoint } from '@/types/healthMonitor';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';

// M3: panel que explica el veredicto del ensemble para la lectura más reciente,
// desglosando los dos detectores y la compuerta AND (poc-dashboard §3.2):
//   Autoencoder: error de reconstrucción vs θ  ->  ¿anómalo?
//   Isolation Forest: ¿punto anómalo?
//   Compuerta AND: alerta sólo si AMBOS coinciden (evita falsos positivos).
// El veredicto del autoencoder se DERIVA como (recon_error > θ); ambos valores
// llegan persistidos por lectura desde el ml-service.

function VerdictBadge({ verdict }: { verdict: boolean | null }) {
  if (verdict == null) {
    return (
      <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
        Sin dato
      </span>
    );
  }
  return verdict ? (
    <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
      Anomalía
    </span>
  ) : (
    <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
      Normal
    </span>
  );
}

function DetectorRow({
  name,
  description,
  verdict,
  detail,
}: {
  name: string;
  description: string;
  verdict: boolean | null;
  detail?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <div>
        <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
          {name}
        </div>
        <div className="text-xs text-zinc-500 dark:text-zinc-400">
          {description}
        </div>
        {detail && (
          <div className="mt-0.5 font-mono text-xs text-zinc-400">{detail}</div>
        )}
      </div>
      <VerdictBadge verdict={verdict} />
    </div>
  );
}

export default function DetectorBreakdownPanel({
  reading,
}: {
  reading: HealthReadingPoint | null;
}) {
  if (!reading) return null;

  const { recon_error, theta, if_anomaly, and_alert, health_state } = reading;
  // Veredicto del autoencoder: error de reconstrucción por encima del umbral θ.
  const aeAnomaly =
    recon_error != null && theta != null ? recon_error > theta : null;
  const cfg = HEALTH_STATE_CONFIG[health_state];

  const fmt = (v: number | null) =>
    v == null
      ? 'n/a'
      : Math.abs(v) >= 1000 || (v !== 0 && Math.abs(v) < 0.001)
        ? v.toExponential(2)
        : v.toFixed(4);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-700 dark:bg-zinc-900">
      <h3 className="mb-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        ¿Por qué este estado? — desglose de detectores
      </h3>
      <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
        El ensemble marca una alerta sólo cuando los <strong>dos</strong>{' '}
        detectores coinciden (compuerta AND). Última lectura evaluada.
      </p>

      <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
        <DetectorRow
          name="Autoencoder (AE)"
          description="Error de reconstrucción vs umbral θ"
          verdict={aeAnomaly}
          detail={`error ${fmt(recon_error)}  ·  θ ${fmt(theta)}`}
        />
        <DetectorRow
          name="Isolation Forest (IF)"
          description="¿La lectura es un punto atípico?"
          verdict={if_anomaly ?? null}
        />
        <DetectorRow
          name="Compuerta AND"
          description="Alerta sólo si AE e IF coinciden"
          verdict={and_alert}
        />
      </div>

      <div className="mt-3 flex items-center justify-between rounded-md bg-zinc-50 px-3 py-2 dark:bg-zinc-800/50">
        <span className="text-sm text-zinc-500 dark:text-zinc-400">
          Estado publicado
        </span>
        <span className="text-sm font-semibold" style={{ color: cfg.color }}>
          {cfg.emoji} {cfg.label}
        </span>
      </div>
    </div>
  );
}
