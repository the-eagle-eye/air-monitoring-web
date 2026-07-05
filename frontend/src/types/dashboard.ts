import type { Equipo } from './lectura';

export interface DashboardData {
  equipos: Equipo[];
}

// KPIs del modelo ensemble (no supervisado). Reemplazan las KPIs RF (RUL,
// predicciones, alertas) que quedaron deprecadas al migrar del Random Forest.
export interface KpiData {
  totalEquipos: number;
  anomalias24h: number;      // equipos con estado anómalo (observado/riesgo/crítico)
  incidenciasAbiertas: number;
  sinTransmision: number;
}

export interface RiskDistribution {
  name: string;
  value: number;
  color: string;
}
