import { fetchEquipos, fetchLecturas } from './lecturas';
import { fetchPredicciones, fetchAlertas } from './predicciones';
import type { DashboardData } from '@/types/dashboard';
import type { Prediccion } from '@/types/prediccion';
import type { LecturaIoT } from '@/types/lectura';

export async function fetchDashboardData(): Promise<DashboardData> {
  const equipos = await fetchEquipos();

  const [predictionResults, alertasResponse] = await Promise.all([
    Promise.allSettled(
      equipos.map((eq) => fetchPredicciones(eq.device_id, 1, 1))
    ),
    fetchAlertas({ page: 1, page_size: 50 }),
  ]);

  const latestPredictions: Record<string, Prediccion> = {};
  predictionResults.forEach((result, index) => {
    if (result.status === 'fulfilled' && result.value.items.length > 0) {
      latestPredictions[equipos[index].device_id] = result.value.items[0];
    }
  });

  return {
    equipos,
    latestPredictions,
    alertas: alertasResponse.items,
    totalAlertas: alertasResponse.total,
  };
}

export async function fetchEquipoLecturas(
  deviceId: string,
): Promise<LecturaIoT[]> {
  const response = await fetchLecturas(deviceId, 1, 100);
  return response.items;
}
