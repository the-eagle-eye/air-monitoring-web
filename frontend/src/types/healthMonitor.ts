// Tipos del monitor de salud no supervisado (ensemble AE+IF+AND).
// Contrato del ml-service (SPEC §6.2).

export type HealthState =
  | 'SANO'
  | 'OBSERVADO'
  | 'EN_RIESGO'
  | 'CRITICO'
  | 'SIN_DATOS';

export interface HealthEvaluateResponse {
  device_id: string;
  timestamp: string;
  recon_error: number | null;
  theta: number | null;
  if_anomaly: boolean | null;
  and_alert: boolean;
  severity: string | null;
  health_state: HealthState;
  hours_since_prev: number | null;
  model_version: string;
}

export interface HealthReadingPoint {
  timestamp: string;
  recon_error: number | null;
  theta: number | null;
  health_state: HealthState;
  and_alert: boolean;
}

export interface HealthReadingsResponse {
  device_id: string;
  points: HealthReadingPoint[];
}

export interface HealthDeviceState {
  device_id: string;
  health_state: HealthState;
  last_recon_error: number | null;
  theta: number | null;
  hours_since_prev: number | null;
  // canal de transmisión (watchdog §1.2), separado del canal de salud
  transmission_state?: 'OK' | 'SIN_TRANSMISION';
  transmission_severity?: 'baja' | 'media' | 'alta' | null;
  last_reading_ts?: string | null;
  updated_at: string;
}

// Config visual por estado (colores del semáforo de Salud Predictiva).
export const HEALTH_STATE_CONFIG: Record<
  HealthState,
  { label: string; color: string; emoji: string; isAlert: boolean }
> = {
  SANO: { label: 'Sano', color: '#22c55e', emoji: '🟢', isAlert: false },
  OBSERVADO: { label: 'Observado', color: '#eab308', emoji: '🟡', isAlert: true },
  EN_RIESGO: { label: 'En riesgo', color: '#f97316', emoji: '🟠', isAlert: true },
  CRITICO: { label: 'Crítico', color: '#ef4444', emoji: '🔴', isAlert: true },
  SIN_DATOS: { label: 'Sin datos', color: '#71717a', emoji: '⚫', isAlert: false },
};
