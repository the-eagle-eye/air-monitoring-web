import type { HealthDeviceState } from '@/types/healthMonitor';

interface EquiposSinTransmisionProps {
  states: Record<string, HealthDeviceState | null>;
}

// Panel separado (poc-dashboard §2.5): los equipos sin transmisión no ensucian
// el semáforo de salud. Es un canal operativo distinto, NO una alerta del sensor.
// Unifica dos casos (spec-transmision §1.2):
//  - SIN_DATOS: transmite pero el dato es inválido (valido=0, gate §3.0)
//  - SIN_TRANSMISION: no transmite nada (detectado por el watchdog)
const SEVERITY_LABEL: Record<string, string> = {
  baja: 'leve (>15 min)',
  media: 'moderado (>1 h)',
  alta: 'crítico (>24 h)',
};

export default function EquiposSinTransmision({
  states,
}: EquiposSinTransmisionProps) {
  const sinDatos = Object.values(states).filter(
    (s): s is HealthDeviceState =>
      s !== null &&
      (s.health_state === 'SIN_DATOS' ||
        s.transmission_state === 'SIN_TRANSMISION'),
  );

  return (
    <div className="rounded-lg border border-zinc-300 bg-zinc-50 p-5 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="flex items-center gap-2">
        <span className="inline-block h-3 w-3 rounded-full bg-zinc-500" />
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Equipos sin transmisión ({sinDatos.length})
        </h2>
      </div>

      {sinDatos.length === 0 ? (
        <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
          Todos los equipos están transmitiendo.
        </p>
      ) : (
        <>
          <ul className="mt-3 divide-y divide-zinc-200 dark:divide-zinc-800">
            {sinDatos.map((s) => {
              const noTx = s.transmission_state === 'SIN_TRANSMISION';
              const motivo = noTx ? 'No transmite' : 'Dato inválido';
              const sev = noTx && s.transmission_severity
                ? SEVERITY_LABEL[s.transmission_severity]
                : null;
              const lastTs = s.last_reading_ts ?? s.updated_at;
              return (
                <li
                  key={s.device_id}
                  className="flex items-center justify-between py-2 text-sm"
                >
                  <span className="flex items-center gap-2">
                    <span className="font-medium text-zinc-800 dark:text-zinc-200">
                      {s.device_id}
                    </span>
                    <span className="rounded bg-zinc-200 px-1.5 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                      {motivo}
                      {sev ? ` · ${sev}` : ''}
                    </span>
                  </span>
                  <span className="text-zinc-500 dark:text-zinc-400">
                    última:{' '}
                    {new Date(lastTs).toLocaleString('es-PE', {
                      day: '2-digit',
                      month: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
            → Revisar PC / energía / enlace. No es una falla del sensor.
          </p>
        </>
      )}
    </div>
  );
}
