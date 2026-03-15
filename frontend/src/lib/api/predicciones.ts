import { apiFetch } from '../api';
import type {
  AlertaListResponse,
  Prediccion,
  PrediccionListResponse,
} from '@/types/prediccion';

export async function runPredictions(
  deviceId?: string,
): Promise<Prediccion[]> {
  return apiFetch<Prediccion[]>('/api/v1/predictions/run', {
    service: 'ml',
    method: 'POST',
    body: JSON.stringify(deviceId ? { device_id: deviceId } : {}),
  });
}

export async function fetchPredicciones(
  deviceId: string,
  page = 1,
  pageSize = 50,
): Promise<PrediccionListResponse> {
  return apiFetch<PrediccionListResponse>(
    `/api/v1/predictions/${deviceId}?page=${page}&page_size=${pageSize}`,
    { service: 'ml' },
  );
}

export async function fetchAlertas(
  params: {
    device_id?: string;
    estado?: string;
    nivel_riesgo?: string;
    page?: number;
    page_size?: number;
  } = {},
): Promise<AlertaListResponse> {
  const searchParams = new URLSearchParams();
  if (params.device_id) searchParams.set('device_id', params.device_id);
  if (params.estado) searchParams.set('estado', params.estado);
  if (params.nivel_riesgo) searchParams.set('nivel_riesgo', params.nivel_riesgo);
  searchParams.set('page', String(params.page ?? 1));
  searchParams.set('page_size', String(params.page_size ?? 50));

  return apiFetch<AlertaListResponse>(
    `/api/v1/alerts?${searchParams.toString()}`,
    { service: 'ml' },
  );
}
