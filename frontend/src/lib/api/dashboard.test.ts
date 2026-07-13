import { fetchDashboardData, fetchEquipoLecturas } from './dashboard';
import * as lecturasApi from './lecturas';
import type { Equipo, LecturaIoT } from '@/types/lectura';

jest.mock('./lecturas');
const mocked = lecturasApi as jest.Mocked<typeof lecturasApi>;

const equipoStub: Equipo = {
  id: 1,
  device_id: 'T101',
  ubicacion: null,
  estacion: null,
  operador: null,
  estado: 'activo',
  fecha_registro: '2026-01-01T00:00:00Z',
} as Equipo;

const lecturaStub: LecturaIoT = {
  id: 10,
  device_id: 'T101',
  timestamp: '2026-07-12T00:00:00Z',
  so2_ppb: 12,
} as LecturaIoT;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('fetchDashboardData', () => {
  it('bundles equipos into the DashboardData shape', async () => {
    mocked.fetchEquipos.mockResolvedValueOnce([equipoStub]);
    await expect(fetchDashboardData()).resolves.toEqual({
      equipos: [equipoStub],
    });
    expect(mocked.fetchEquipos).toHaveBeenCalledTimes(1);
  });
});

describe('fetchEquipoLecturas', () => {
  it('requests page 1 with page_size 100 and unwraps items', async () => {
    mocked.fetchLecturas.mockResolvedValueOnce({
      items: [lecturaStub],
      total: 1,
      page: 1,
      page_size: 100,
    });
    await expect(fetchEquipoLecturas('T101')).resolves.toEqual([lecturaStub]);
    expect(mocked.fetchLecturas).toHaveBeenCalledWith('T101', 1, 100);
  });
});
