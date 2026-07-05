import { fetchEquipos, fetchLecturas } from './lecturas';
import type { DashboardData } from '@/types/dashboard';
import type { LecturaIoT } from '@/types/lectura';

// El dashboard usa el modelo ensemble (salud) — los datos de salud por equipo se
// cargan aparte con fetchHealthStates. Aquí solo se traen los equipos.
export async function fetchDashboardData(): Promise<DashboardData> {
  const equipos = await fetchEquipos();
  return { equipos };
}

export async function fetchEquipoLecturas(
  deviceId: string,
): Promise<LecturaIoT[]> {
  const response = await fetchLecturas(deviceId, 1, 100);
  return response.items;
}
