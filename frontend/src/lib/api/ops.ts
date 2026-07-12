import { apiFetch } from '../api';
import { SERVICE_URLS } from '../api';
import type {
  Incidencia,
  IncidenciaListResponse,
  Problema,
  ProblemaListResponse,
  CalibracionOps,
  CalibracionListResponse,
  Mantenimiento,
  ReportePreviewResponse,
  Usuario,
  UsuarioCreate,
  UsuarioUpdate,
  Proveedor,
  ProveedorCreate,
  ProveedorUpdate,
  Repuesto,
  RepuestoCreate,
  RepuestoUpdate,
} from '@/types/ops';

// --- Incidencias ---

export async function fetchIncidencias(params?: {
  device_id?: string;
  tipo?: string;
  estado?: string;
  page?: number;
  page_size?: number;
}): Promise<IncidenciaListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.device_id) searchParams.set('device_id', params.device_id);
  if (params?.tipo) searchParams.set('tipo', params.tipo);
  if (params?.estado) searchParams.set('estado', params.estado);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size)
    searchParams.set('page_size', String(params.page_size));
  const qs = searchParams.toString();
  return apiFetch<IncidenciaListResponse>(
    `/api/v1/incidencias${qs ? `?${qs}` : ''}`,
    { service: 'gateway' },
  );
}

export async function fetchIncidencia(id: number): Promise<Incidencia> {
  return apiFetch<Incidencia>(`/api/v1/incidencias/${id}`, {
    service: 'gateway',
  });
}

export async function createIncidencia(data: {
  device_id: string;
  tipo: string;
  descripcion?: string;
  prioridad?: string;
  impacto?: string;
  urgencia?: string;
  categoria?: string;
  responsable_id?: number;
}): Promise<Incidencia> {
  return apiFetch<Incidencia>('/api/v1/incidencias', {
    service: 'gateway',
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateIncidencia(
  id: number,
  data: {
    estado?: string;
    responsable_id?: number;
    descripcion?: string;
    impacto?: string;
    urgencia?: string;
    categoria?: string;
    problema_id?: number | null;
  },
): Promise<Incidencia> {
  return apiFetch<Incidencia>(`/api/v1/incidencias/${id}`, {
    service: 'gateway',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// Vincular/desvincular incidencia a un problema (ITIL)
export async function linkIncidenciaProblema(
  incidenciaId: number,
  problemaId: number | null,
): Promise<Incidencia> {
  return apiFetch<Incidencia>(`/api/v1/incidencias/${incidenciaId}/problema`, {
    service: 'gateway',
    method: 'POST',
    body: JSON.stringify({ problema_id: problemaId }),
  });
}

export async function submitMantenimiento(
  incidenciaId: number,
  data: {
    diagnostico?: string;
    acciones_realizadas?: string;
    conclusion?: string;
    fecha_ejecucion?: string;
    repuesto_ids?: number[];
    adjuntos?: { filename: string; file_url: string }[];
  },
): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>(
    `/api/v1/incidencias/${incidenciaId}/mantenimiento`,
    {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify(data),
    },
  );
}

// --- Repuestos ---

export async function fetchRepuestos(categoria?: string): Promise<Repuesto[]> {
  const qs = categoria ? `?categoria=${categoria}` : '';
  return apiFetch<Repuesto[]>(`/api/v1/repuestos${qs}`, { service: 'gateway' });
}

export async function createRepuesto(data: RepuestoCreate): Promise<Repuesto> {
  return apiFetch<Repuesto>('/api/v1/repuestos', {
    service: 'gateway',
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateRepuesto(
  id: number,
  data: RepuestoUpdate,
): Promise<Repuesto> {
  return apiFetch<Repuesto>(`/api/v1/repuestos/${id}`, {
    service: 'gateway',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteRepuesto(id: number): Promise<void> {
  await apiFetch(`/api/v1/repuestos/${id}`, {
    service: 'gateway',
    method: 'DELETE',
  });
}

// --- Calibraciones ---

export async function fetchCalibracionesOps(params?: {
  device_id?: string;
  page?: number;
  page_size?: number;
}): Promise<CalibracionListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.device_id) searchParams.set('device_id', params.device_id);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size)
    searchParams.set('page_size', String(params.page_size));
  const qs = searchParams.toString();
  return apiFetch<CalibracionListResponse>(
    `/api/v1/calibraciones${qs ? `?${qs}` : ''}`,
    { service: 'gateway' },
  );
}

export async function fetchCalibracion(id: number): Promise<CalibracionOps> {
  return apiFetch<CalibracionOps>(`/api/v1/calibraciones/${id}`, {
    service: 'gateway',
  });
}

export async function createCalibracion(data: {
  device_id: string;
  incidencia_id?: number;
  fecha_calibracion?: string;
  nota?: string;
  certificado_url?: string;
  proveedor_id?: number;
}): Promise<CalibracionOps> {
  return apiFetch<CalibracionOps>('/api/v1/calibraciones', {
    service: 'gateway',
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCalibracion(
  id: number,
  data: {
    fecha_calibracion?: string;
    nota?: string;
    certificado_url?: string;
    proveedor_id?: number;
  },
): Promise<CalibracionOps> {
  return apiFetch<CalibracionOps>(`/api/v1/calibraciones/${id}`, {
    service: 'gateway',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// --- Proveedores ---

export async function fetchProveedores(): Promise<Proveedor[]> {
  return apiFetch<Proveedor[]>('/api/v1/proveedores', { service: 'gateway' });
}

export async function createProveedor(
  data: ProveedorCreate,
): Promise<Proveedor> {
  return apiFetch<Proveedor>('/api/v1/proveedores', {
    service: 'gateway',
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProveedor(
  id: number,
  data: ProveedorUpdate,
): Promise<Proveedor> {
  return apiFetch<Proveedor>(`/api/v1/proveedores/${id}`, {
    service: 'gateway',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteProveedor(id: number): Promise<void> {
  await apiFetch(`/api/v1/proveedores/${id}`, {
    service: 'gateway',
    method: 'DELETE',
  });
}

// --- Usuarios ---

export async function fetchUsuarios(): Promise<Usuario[]> {
  return apiFetch<Usuario[]>('/api/v1/usuarios', { service: 'gateway' });
}

export async function createUsuario(data: UsuarioCreate): Promise<Usuario> {
  return apiFetch<Usuario>('/api/v1/usuarios', {
    service: 'gateway',
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateUsuario(
  id: number,
  data: UsuarioUpdate,
): Promise<Usuario> {
  return apiFetch<Usuario>(`/api/v1/usuarios/${id}`, {
    service: 'gateway',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteUsuario(id: number): Promise<void> {
  await apiFetch(`/api/v1/usuarios/${id}`, {
    service: 'gateway',
    method: 'DELETE',
  });
}

// --- Reportes ---

export interface ReporteParams {
  fecha_inicio?: string;
  fecha_fin?: string;
  device_id?: string;
  tipo?: string;
}

function buildReporteQuery(params?: ReporteParams): string {
  const searchParams = new URLSearchParams();
  if (params?.fecha_inicio)
    searchParams.set('fecha_inicio', params.fecha_inicio);
  if (params?.fecha_fin) searchParams.set('fecha_fin', params.fecha_fin);
  if (params?.device_id) searchParams.set('device_id', params.device_id);
  if (params?.tipo) searchParams.set('tipo', params.tipo);
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

export async function fetchReportePreview(
  params?: ReporteParams,
): Promise<ReportePreviewResponse> {
  return apiFetch<ReportePreviewResponse>(
    `/api/v1/reportes/preview${buildReporteQuery(params)}`,
    { service: 'gateway' },
  );
}

export async function downloadReporte(
  format: 'csv' | 'pdf',
  params?: ReporteParams,
): Promise<void> {
  const url = `${SERVICE_URLS.gateway}/api/v1/reportes/${format}${buildReporteQuery(params)}`;
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const resp = await fetch(url, { headers });

  if (!resp.ok) {
    const error = await resp.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP ${resp.status}`);
  }

  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `reporte_mantenimiento.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

// --- Problemas (ITIL v4 gestión de problemas) ---

export async function fetchProblemas(params?: {
  estado?: string;
  device_id?: string;
}): Promise<ProblemaListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.estado) searchParams.set('estado', params.estado);
  if (params?.device_id) searchParams.set('device_id', params.device_id);
  const qs = searchParams.toString();
  return apiFetch<ProblemaListResponse>(
    `/api/v1/problemas${qs ? `?${qs}` : ''}`,
    { service: 'gateway' },
  );
}

export async function fetchProblema(id: number): Promise<Problema> {
  return apiFetch<Problema>(`/api/v1/problemas/${id}`, { service: 'gateway' });
}

export async function fetchProblemaIncidencias(
  id: number,
): Promise<Incidencia[]> {
  return apiFetch<Incidencia[]>(`/api/v1/problemas/${id}/incidencias`, {
    service: 'gateway',
  });
}

export async function createProblema(data: {
  titulo: string;
  device_id?: string;
  descripcion?: string;
  causa_raiz?: string;
}): Promise<Problema> {
  return apiFetch<Problema>('/api/v1/problemas', {
    service: 'gateway',
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProblema(
  id: number,
  data: {
    titulo?: string;
    descripcion?: string;
    estado?: string;
    causa_raiz?: string;
  },
): Promise<Problema> {
  return apiFetch<Problema>(`/api/v1/problemas/${id}`, {
    service: 'gateway',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ITIL: equipos con correctivas recurrentes -> sugerencia de abrir un Problema.
export interface EquipoReincidente {
  device_id: string;
  correctivas: number;
  desde: string;
  incidencia_ids: number[];
}

export interface ReincidentesResponse {
  dias: number;
  min_correctivas: number;
  items: EquipoReincidente[];
}

export async function fetchReincidentes(params?: {
  dias?: number;
  min_correctivas?: number;
}): Promise<ReincidentesResponse> {
  const sp = new URLSearchParams();
  if (params?.dias) sp.set('dias', String(params.dias));
  if (params?.min_correctivas)
    sp.set('min_correctivas', String(params.min_correctivas));
  const qs = sp.toString();
  return apiFetch<ReincidentesResponse>(
    `/api/v1/problemas/reincidentes${qs ? `?${qs}` : ''}`,
    { service: 'gateway' },
  );
}

export interface ProblemasResumen {
  por_estado: Record<string, number>;
  abiertos: number;
  total: number;
}

export async function fetchProblemasResumen(): Promise<ProblemasResumen> {
  return apiFetch<ProblemasResumen>('/api/v1/problemas/resumen', {
    service: 'gateway',
  });
}
