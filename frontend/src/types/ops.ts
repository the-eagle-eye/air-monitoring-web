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
  mantenimiento_correctivo?: Mantenimiento | null;
}

export interface IncidenciaListResponse {
  items: Incidencia[];
  total: number;
  page: number;
  page_size: number;
}

export interface CalibracionOps {
  id: number;
  incidencia_id: number | null;
  device_id: string;
  fecha_calibracion: string | null;
  nota: string | null;
  certificado_url: string | null;
  proveedor_id: number | null;
  estado: string;
  incidencia_estado: string | null;
  created_at: string;
}

export interface CalibracionListResponse {
  items: CalibracionOps[];
  total: number;
  page: number;
  page_size: number;
}

export interface RepuestoUsado {
  id: number;
  nombre: string;
  categoria: string;
}

export interface AdjuntoResponse {
  id: number;
  filename: string;
  file_url: string;
}

export interface Mantenimiento {
  id: number;
  incidencia_id: number;
  diagnostico: string | null;
  acciones_realizadas: string | null;
  conclusion: string | null;
  fecha_ejecucion: string | null;
  repuestos: RepuestoUsado[];
  adjuntos: AdjuntoResponse[];
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

export interface Repuesto {
  id: number;
  nombre: string;
  categoria: string;
  estado: string;
  created_at: string;
}

export interface AdjuntoInput {
  filename: string;
  file_url: string;
}
