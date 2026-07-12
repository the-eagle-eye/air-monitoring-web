import { apiFetch } from '../api';
import type {
  HealthDeviceState,
  HealthEvaluateResponse,
  HealthReadingsResponse,
} from '@/types/healthMonitor';

// Serie histórica de recon_error + θ para el gráfico de tendencia de salud.
export async function fetchHealthReadings(
  deviceId: string,
  limit = 300,
): Promise<HealthReadingsResponse> {
  return apiFetch<HealthReadingsResponse>(
    `/api/v1/health-monitor/${deviceId}/readings?limit=${limit}`,
    { service: 'gateway' },
  );
}

// Estado vigente de salud por equipo (semáforo de "Salud predictiva").
export async function fetchHealthState(
  deviceId: string,
): Promise<HealthDeviceState> {
  return apiFetch<HealthDeviceState>(
    `/api/v1/health-monitor/${deviceId}/state`,
    { service: 'gateway' },
  );
}

// Evalúa una lectura contra el ensemble (uso interno / pruebas).
export async function evaluateReading(reading: {
  device_id: string;
  timestamp: string;
  so2_ppb?: number | null;
  so2_flow?: number | null;
  so2_internal_temp?: number | null;
  so2_lamp_int?: number | null;
  valido: number;
}): Promise<HealthEvaluateResponse> {
  return apiFetch<HealthEvaluateResponse>('/api/v1/health-monitor/evaluate', {
    service: 'gateway',
    method: 'POST',
    body: JSON.stringify(reading),
  });
}

// Estado de varios equipos (para el semáforo agregado). Tolera 404 por equipo
// (equipo sin estado aún) devolviendo null en su lugar.
export async function fetchHealthStates(
  deviceIds: string[],
): Promise<Record<string, HealthDeviceState | null>> {
  const entries = await Promise.all(
    deviceIds.map(async (id) => {
      try {
        return [id, await fetchHealthState(id)] as const;
      } catch {
        return [id, null] as const;
      }
    }),
  );
  return Object.fromEntries(entries);
}
