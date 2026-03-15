import { apiFetch } from '../api';
import type {
  Incidencia,
  IncidenciaListResponse,
  CalibracionOps,
  CalibracionListResponse,
  Mantenimiento,
  Usuario,
  Proveedor,
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
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));
  const qs = searchParams.toString();
  return apiFetch<IncidenciaListResponse>(
    `/api/v1/incidencias${qs ? `?${qs}` : ''}`,
    { service: 'ops' },
  );
}

export async function fetchIncidencia(id: number): Promise<Incidencia> {
  return apiFetch<Incidencia>(`/api/v1/incidencias/${id}`, { service: 'ops' });
}

export async function createIncidencia(data: {
  device_id: string;
  tipo: string;
  descripcion?: string;
  prioridad?: string;
  responsable_id?: number;
}): Promise<Incidencia> {
  return apiFetch<Incidencia>('/api/v1/incidencias', {
    service: 'ops',
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
  },
): Promise<Incidencia> {
  return apiFetch<Incidencia>(`/api/v1/incidencias/${id}`, {
    service: 'ops',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function submitMantenimiento(
  incidenciaId: number,
  data: {
    diagnostico?: string;
    acciones_realizadas?: string;
    conclusion?: string;
    repuesto_ids?: number[];
  },
): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>(
    `/api/v1/incidencias/${incidenciaId}/mantenimiento`,
    {
      service: 'ops',
      method: 'POST',
      body: JSON.stringify(data),
    },
  );
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
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));
  const qs = searchParams.toString();
  return apiFetch<CalibracionListResponse>(
    `/api/v1/calibraciones${qs ? `?${qs}` : ''}`,
    { service: 'ops' },
  );
}

export async function fetchCalibracion(id: number): Promise<CalibracionOps> {
  return apiFetch<CalibracionOps>(`/api/v1/calibraciones/${id}`, {
    service: 'ops',
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
    service: 'ops',
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
    service: 'ops',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// --- Usuarios y Proveedores ---

export async function fetchUsuarios(): Promise<Usuario[]> {
  return apiFetch<Usuario[]>('/api/v1/usuarios', { service: 'ops' });
}

export async function fetchProveedores(): Promise<Proveedor[]> {
  return apiFetch<Proveedor[]>('/api/v1/proveedores', { service: 'ops' });
}
