import type { Equipo } from './lectura';
import type { Prediccion, Alerta } from './prediccion';

export interface DashboardData {
  equipos: Equipo[];
  latestPredictions: Record<string, Prediccion>;
  alertas: Alerta[];
  totalAlertas: number;
}

export interface KpiData {
  totalEquipos: number;
  alertasAltas: number;
  rulPromedio: number;
  prediccionesRecientes: number;
}

export interface RiskDistribution {
  name: string;
  value: number;
  color: string;
}

export interface EquipoHealth {
  equipo: Equipo;
  prediction: Prediccion | null;
}
