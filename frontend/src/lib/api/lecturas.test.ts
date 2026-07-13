import {
  fetchLecturas,
  fetchEquipos,
  fetchEquipo,
  createEquipo,
  updateEquipo,
  deleteEquipo,
  fetchEquiposPendientes,
  confirmarEquipo,
} from './lecturas';
import { apiFetch } from '../api';

jest.mock('../api');
const mockApi = apiFetch as jest.MockedFunction<typeof apiFetch>;

beforeEach(() => {
  mockApi.mockReset();
  mockApi.mockResolvedValue({} as never);
});

describe('lecturas API', () => {
  it('fetchLecturas uses default page/page_size and iot service', async () => {
    await fetchLecturas('T101');
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/iot/readings/T101?page=1&page_size=50',
      { service: 'iot' },
    );
  });

  it('fetchLecturas honors overridden page + page_size', async () => {
    await fetchLecturas('T101', 3, 25);
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/iot/readings/T101?page=3&page_size=25',
      { service: 'iot' },
    );
  });

  it('fetchEquipos targets the iot equipos list', async () => {
    await fetchEquipos();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/iot/equipos', {
      service: 'iot',
    });
  });

  it('fetchEquipo interpolates the device id', async () => {
    await fetchEquipo('T101');
    expect(mockApi).toHaveBeenCalledWith('/api/v1/iot/equipos/T101', {
      service: 'iot',
    });
  });

  it('createEquipo POSTs the payload as JSON', async () => {
    await createEquipo({ device_id: 'T999', ubicacion: 'Lima' } as never);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/iot/equipos', {
      service: 'iot',
      method: 'POST',
      body: JSON.stringify({ device_id: 'T999', ubicacion: 'Lima' }),
    });
  });

  it('updateEquipo PUTs to /equipos/{id} with the diff', async () => {
    await updateEquipo('T101', { ubicacion: 'Ilo' } as never);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/iot/equipos/T101', {
      service: 'iot',
      method: 'PUT',
      body: JSON.stringify({ ubicacion: 'Ilo' }),
    });
  });

  it('deleteEquipo issues DELETE', async () => {
    await deleteEquipo('T101');
    expect(mockApi).toHaveBeenCalledWith('/api/v1/iot/equipos/T101', {
      service: 'iot',
      method: 'DELETE',
    });
  });

  it('fetchEquiposPendientes hits /equipos/pendientes', async () => {
    await fetchEquiposPendientes();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/iot/equipos/pendientes', {
      service: 'iot',
    });
  });

  it('confirmarEquipo POSTs {} by default', async () => {
    await confirmarEquipo('T101');
    expect(mockApi).toHaveBeenCalledWith('/api/v1/iot/equipos/T101/confirmar', {
      service: 'iot',
      method: 'POST',
      body: JSON.stringify({}),
    });
  });

  it('confirmarEquipo forwards overrides', async () => {
    await confirmarEquipo('T101', { ubicacion: 'Ilo' } as never);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/iot/equipos/T101/confirmar', {
      service: 'iot',
      method: 'POST',
      body: JSON.stringify({ ubicacion: 'Ilo' }),
    });
  });
});
