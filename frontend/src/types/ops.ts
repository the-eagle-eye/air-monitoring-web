export interface Incidencia {
  id: number;
  device_id: string;
  tipo: string;
  descripcion: string | null;
  estado: string;
  prioridad: string;
  responsable_id: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface IncidenciaListResponse {
  items: Incidencia[];
  total: number;
  page: number;
  page_size: number;
}

export interface CalibracionOps {
  id: number;
  incidencia_id: number;
  device_id: string;
  fecha_calibracion: string | null;
  nota: string | null;
  certificado_url: string | null;
  proveedor_id: number | null;
  created_at: string;
}

export interface CalibracionListResponse {
  items: CalibracionOps[];
  total: number;
  page: number;
  page_size: number;
}

export interface Mantenimiento {
  id: number;
  incidencia_id: number;
  diagnostico: string | null;
  acciones_realizadas: string | null;
  conclusion: string | null;
  fecha_ejecucion: string | null;
  created_at: string;
}

export interface Usuario {
  id: number;
  email: string;
  nombre: string;
  apellido: string;
  rol: string;
  estado: string;
}

export interface Proveedor {
  id: number;
  nombre: string;
  estado: string;
}
