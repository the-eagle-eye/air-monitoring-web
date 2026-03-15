import { apiFetch } from '../api';
import type { Equipo, LecturaIoTListResponse } from '@/types/lectura';

export async function fetchLecturas(
  deviceId: string,
  page = 1,
  pageSize = 50,
): Promise<LecturaIoTListResponse> {
  return apiFetch<LecturaIoTListResponse>(
    `/api/v1/iot/readings/${deviceId}?page=${page}&page_size=${pageSize}`,
    { service: 'iot' },
  );
}

export async function fetchEquipos(): Promise<Equipo[]> {
  return apiFetch<Equipo[]>('/api/v1/iot/equipos', { service: 'iot' });
}

export async function fetchEquipo(deviceId: string): Promise<Equipo> {
  return apiFetch<Equipo>(`/api/v1/iot/equipos/${deviceId}`, { service: 'iot' });
}

export async function createEquipo(
  data: Partial<Equipo> & { device_id: string },
): Promise<Equipo> {
  return apiFetch<Equipo>('/api/v1/iot/equipos', {
    service: 'iot',
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateEquipo(
  deviceId: string,
  data: Partial<Omit<Equipo, 'id' | 'device_id' | 'fecha_registro'>>,
): Promise<Equipo> {
  return apiFetch<Equipo>(`/api/v1/iot/equipos/${deviceId}`, {
    service: 'iot',
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteEquipo(deviceId: string): Promise<{ detail: string }> {
  return apiFetch<{ detail: string }>(`/api/v1/iot/equipos/${deviceId}`, {
    service: 'iot',
    method: 'DELETE',
  });
}
