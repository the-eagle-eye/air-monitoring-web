export interface Prediccion {
  id: number;
  device_id: string;
  model_version: string;
  prediction_timestamp: string;
  failure_probability: number;
  remaining_useful_life_days: number;
  risk_level: 'alta' | 'media' | 'baja';
  created_at: string;
}

export interface PrediccionDetail extends Prediccion {
  feature_snapshot: Record<string, number> | null;
}

export interface PrediccionListResponse {
  items: Prediccion[];
  total: number;
  page: number;
  page_size: number;
}

export interface Alerta {
  id: number;
  device_id: string;
  prediccion_id: number;
  nivel_riesgo: 'alta' | 'media' | 'baja';
  descripcion: string | null;
  estado: string;
  created_at: string;
}

export interface AlertaListResponse {
  items: Alerta[];
  total: number;
  page: number;
  page_size: number;
}
