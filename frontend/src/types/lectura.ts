export interface LecturaIoT {
  id: number;
  device_id: number;
  equipo_device_id: string;
  timestamp_lectura: string;
  // Legacy flat sensor columns (still returned by some responses).
  so2_ppb?: number | null;
  h2s_ppb?: number | null;
  reaction_temp?: number | null;
  izs_temp?: number | null;
  pmt_temp?: number | null;
  sample_flow?: number | null;
  pressure?: number | null;
  uv_lamp_intensity?: number | null;
  box_temp?: number | null;
  hvps_v?: number | null;
  conv_temp?: number | null;
  ozone_flow?: number | null;
  // Post-migration-004 shape: sensors nested under a JSONB column with
  // mixed-case Thermo-analyzer keys (SO2_ppb, Box_Temp, UVLampIntensity, ...).
  sensors?: Record<string, number | string | null>;
  procesado: boolean;
  created_at: string;
}

export interface LecturaIoTDetail extends LecturaIoT {
  raw_payload: Record<string, unknown> | null;
}

export interface LecturaIoTListResponse {
  items: LecturaIoT[];
  total: number;
  page: number;
  page_size: number;
}

export interface Equipo {
  id: number;
  device_id: string;
  nombre: string | null;
  tipo: string | null;
  ubicacion: string | null;
  estado: string;
  serie: string | null;
  codigo_interno: string | null;
  modelo: string | null;
  marca: string | null;
  fecha_ingreso: string | null;
  rango_medicion: string | null;
  parametro_medicion: string | null;
  foto_equipo: string | null;
  datalogger_id: number | null;
  criticidad?: string;
  fecha_registro: string;
  fecha_actualizacion: string | null;
}
