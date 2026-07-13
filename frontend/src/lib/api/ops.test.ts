import * as ops from './ops';
import { apiFetch, SERVICE_URLS } from '../api';

jest.mock('../api', () => {
  const actual = jest.requireActual('../api');
  return {
    ...actual,
    apiFetch: jest.fn(),
  };
});

const mockApi = apiFetch as jest.MockedFunction<typeof apiFetch>;

beforeEach(() => {
  mockApi.mockReset();
  mockApi.mockResolvedValue({} as never);
});

// --- Incidencias -----------------------------------------------------------

describe('fetchIncidencias', () => {
  it('omits the query string when no filters are given', async () => {
    await ops.fetchIncidencias();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/incidencias', {
      service: 'gateway',
    });
  });

  it('serializes all filter params', async () => {
    await ops.fetchIncidencias({
      device_id: 'T101',
      tipo: 'correctiva',
      estado: 'pendiente',
      page: 2,
      page_size: 10,
    });
    const [url] = mockApi.mock.calls[0];
    expect(url).toBe(
      '/api/v1/incidencias?device_id=T101&tipo=correctiva&estado=pendiente&page=2&page_size=10',
    );
  });

  it('serializes only the params provided', async () => {
    await ops.fetchIncidencias({ tipo: 'calibracion' });
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/incidencias?tipo=calibracion',
      { service: 'gateway' },
    );
  });
});

describe('fetchIncidencia', () => {
  it('interpolates the id', async () => {
    await ops.fetchIncidencia(42);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/incidencias/42', {
      service: 'gateway',
    });
  });
});

describe('createIncidencia', () => {
  it('POSTs the payload', async () => {
    const data = { device_id: 'T101', tipo: 'correctiva' };
    await ops.createIncidencia(data);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/incidencias', {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify(data),
    });
  });
});

describe('updateIncidencia', () => {
  it('PUTs to /incidencias/{id} with the diff', async () => {
    await ops.updateIncidencia(1, { estado: 'en_ejecucion' });
    expect(mockApi).toHaveBeenCalledWith('/api/v1/incidencias/1', {
      service: 'gateway',
      method: 'PUT',
      body: JSON.stringify({ estado: 'en_ejecucion' }),
    });
  });
});

describe('linkIncidenciaProblema', () => {
  it('POSTs problema_id (number) to /incidencias/{id}/problema', async () => {
    await ops.linkIncidenciaProblema(5, 7);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/incidencias/5/problema', {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify({ problema_id: 7 }),
    });
  });

  it('POSTs problema_id null to detach', async () => {
    await ops.linkIncidenciaProblema(5, null);
    const body = JSON.parse(mockApi.mock.calls[0][1]!.body as string);
    expect(body).toEqual({ problema_id: null });
  });
});

describe('submitMantenimiento', () => {
  it('POSTs mantenimiento data under /incidencias/{id}/mantenimiento', async () => {
    const data = {
      diagnostico: 'sensor sucio',
      acciones_realizadas: 'limpieza',
      repuesto_ids: [1, 2],
    };
    await ops.submitMantenimiento(9, data);
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/incidencias/9/mantenimiento',
      {
        service: 'gateway',
        method: 'POST',
        body: JSON.stringify(data),
      },
    );
  });
});

// --- Repuestos -------------------------------------------------------------

describe('repuestos', () => {
  it('fetchRepuestos with no categoria omits the query string', async () => {
    await ops.fetchRepuestos();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/repuestos', {
      service: 'gateway',
    });
  });

  it('fetchRepuestos appends the categoria filter', async () => {
    await ops.fetchRepuestos('lampara');
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/repuestos?categoria=lampara',
      { service: 'gateway' },
    );
  });

  it('createRepuesto POSTs the payload', async () => {
    const data = { nombre: 'Filtro', categoria: 'lampara' } as never;
    await ops.createRepuesto(data);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/repuestos', {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify(data),
    });
  });

  it('updateRepuesto PUTs to /repuestos/{id}', async () => {
    await ops.updateRepuesto(3, { nombre: 'Filtro-v2' } as never);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/repuestos/3', {
      service: 'gateway',
      method: 'PUT',
      body: JSON.stringify({ nombre: 'Filtro-v2' }),
    });
  });

  it('deleteRepuesto issues DELETE', async () => {
    await ops.deleteRepuesto(3);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/repuestos/3', {
      service: 'gateway',
      method: 'DELETE',
    });
  });
});

// --- Calibraciones ---------------------------------------------------------

describe('calibraciones', () => {
  it('fetchCalibracionesOps omits qs when no params', async () => {
    await ops.fetchCalibracionesOps();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/calibraciones', {
      service: 'gateway',
    });
  });

  it('fetchCalibracionesOps serializes device_id + page + page_size', async () => {
    await ops.fetchCalibracionesOps({
      device_id: 'T101',
      page: 2,
      page_size: 20,
    });
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/calibraciones?device_id=T101&page=2&page_size=20',
      { service: 'gateway' },
    );
  });

  it('fetchCalibracion interpolates the id', async () => {
    await ops.fetchCalibracion(11);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/calibraciones/11', {
      service: 'gateway',
    });
  });

  it('createCalibracion POSTs the payload', async () => {
    const data = { device_id: 'T101', nota: 'ok' };
    await ops.createCalibracion(data);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/calibraciones', {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify(data),
    });
  });

  it('updateCalibracion PUTs the diff', async () => {
    await ops.updateCalibracion(11, { nota: 'verificada' });
    expect(mockApi).toHaveBeenCalledWith('/api/v1/calibraciones/11', {
      service: 'gateway',
      method: 'PUT',
      body: JSON.stringify({ nota: 'verificada' }),
    });
  });
});

// --- Proveedores -----------------------------------------------------------

describe('proveedores', () => {
  it('fetchProveedores hits /proveedores', async () => {
    await ops.fetchProveedores();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/proveedores', {
      service: 'gateway',
    });
  });

  it('createProveedor POSTs the payload', async () => {
    const data = { nombre: 'ProvX' } as never;
    await ops.createProveedor(data);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/proveedores', {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify(data),
    });
  });

  it('updateProveedor PUTs the diff', async () => {
    await ops.updateProveedor(4, { nombre: 'ProvY' } as never);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/proveedores/4', {
      service: 'gateway',
      method: 'PUT',
      body: JSON.stringify({ nombre: 'ProvY' }),
    });
  });

  it('deleteProveedor issues DELETE', async () => {
    await ops.deleteProveedor(4);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/proveedores/4', {
      service: 'gateway',
      method: 'DELETE',
    });
  });
});

// --- Usuarios --------------------------------------------------------------

describe('usuarios', () => {
  it('fetchUsuarios hits /usuarios', async () => {
    await ops.fetchUsuarios();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/usuarios', {
      service: 'gateway',
    });
  });

  it('createUsuario POSTs the payload', async () => {
    const data = { email: 'x@y.com' } as never;
    await ops.createUsuario(data);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/usuarios', {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify(data),
    });
  });

  it('updateUsuario PUTs the diff', async () => {
    await ops.updateUsuario(2, { nombre: 'Nuevo' } as never);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/usuarios/2', {
      service: 'gateway',
      method: 'PUT',
      body: JSON.stringify({ nombre: 'Nuevo' }),
    });
  });

  it('deleteUsuario issues DELETE', async () => {
    await ops.deleteUsuario(2);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/usuarios/2', {
      service: 'gateway',
      method: 'DELETE',
    });
  });
});

// --- Reportes --------------------------------------------------------------

describe('reportes', () => {
  it('fetchReportePreview with no params omits the query string', async () => {
    await ops.fetchReportePreview();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/reportes/preview', {
      service: 'gateway',
    });
  });

  it('fetchReportePreview serializes each supported filter', async () => {
    await ops.fetchReportePreview({
      fecha_inicio: '2026-01-01',
      fecha_fin: '2026-01-31',
      device_id: 'T101',
      tipo: 'correctiva',
    });
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/reportes/preview?fecha_inicio=2026-01-01&fecha_fin=2026-01-31&device_id=T101&tipo=correctiva',
      { service: 'gateway' },
    );
  });

  describe('downloadReporte', () => {
    let originalFetch: typeof global.fetch;
    let createObjectURL: jest.Mock;
    let revokeObjectURL: jest.Mock;
    let appendSpy: jest.SpyInstance;
    let removeSpy: jest.SpyInstance;
    let clickSpy: jest.SpyInstance;

    beforeEach(() => {
      originalFetch = global.fetch;
      createObjectURL = jest.fn(() => 'blob:mock');
      revokeObjectURL = jest.fn();
      // jsdom does not implement these — install lightweight stubs.
      (URL as unknown as { createObjectURL: jest.Mock }).createObjectURL =
        createObjectURL;
      (URL as unknown as { revokeObjectURL: jest.Mock }).revokeObjectURL =
        revokeObjectURL;
      appendSpy = jest
        .spyOn(document.body, 'appendChild')
        .mockImplementation((n) => n as never);
      removeSpy = jest
        .spyOn(document.body, 'removeChild')
        .mockImplementation((n) => n as never);
      clickSpy = jest
        .spyOn(HTMLAnchorElement.prototype, 'click')
        .mockImplementation(() => {});
    });

    afterEach(() => {
      global.fetch = originalFetch;
      appendSpy.mockRestore();
      removeSpy.mockRestore();
      clickSpy.mockRestore();
      localStorage.clear();
    });

    function mockBlobFetch(ok = true, status = 200, detail?: string) {
      const blob = new Blob(['x'], { type: 'text/csv' });
      global.fetch = jest.fn().mockResolvedValue({
        ok,
        status,
        blob: () => Promise.resolve(blob),
        json: () => Promise.resolve(detail ? { detail } : {}),
      } as unknown as Response);
    }

    it('hits /reportes/{format} with the built query string and no Authorization when unauthenticated', async () => {
      mockBlobFetch();
      await ops.downloadReporte('csv', { device_id: 'T101' });
      const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toBe(
        `${SERVICE_URLS.gateway}/api/v1/reportes/csv?device_id=T101`,
      );
      expect(opts.headers).toEqual({});
      expect(clickSpy).toHaveBeenCalled();
      expect(revokeObjectURL).toHaveBeenCalled();
    });

    it('attaches the Bearer token when a token is stored', async () => {
      localStorage.setItem('token', 'tok');
      mockBlobFetch();
      await ops.downloadReporte('pdf');
      const [, opts] = (global.fetch as jest.Mock).mock.calls[0];
      expect(opts.headers.Authorization).toBe('Bearer tok');
    });

    it('surfaces the server detail on failure', async () => {
      mockBlobFetch(false, 500, 'boom');
      await expect(ops.downloadReporte('csv')).rejects.toThrow('boom');
    });

    it('falls back to HTTP {status} when there is no detail', async () => {
      mockBlobFetch(false, 502);
      await expect(ops.downloadReporte('csv')).rejects.toThrow('HTTP 502');
    });
  });
});

// --- Problemas -------------------------------------------------------------

describe('problemas', () => {
  it('fetchProblemas omits qs by default', async () => {
    await ops.fetchProblemas();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/problemas', {
      service: 'gateway',
    });
  });

  it('fetchProblemas serializes estado + device_id', async () => {
    await ops.fetchProblemas({ estado: 'abierto', device_id: 'T101' });
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/problemas?estado=abierto&device_id=T101',
      { service: 'gateway' },
    );
  });

  it('fetchProblema interpolates the id', async () => {
    await ops.fetchProblema(7);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/problemas/7', {
      service: 'gateway',
    });
  });

  it('fetchProblemaIncidencias hits the nested endpoint', async () => {
    await ops.fetchProblemaIncidencias(7);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/problemas/7/incidencias', {
      service: 'gateway',
    });
  });

  it('createProblema POSTs the payload', async () => {
    const data = { titulo: 'X' };
    await ops.createProblema(data);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/problemas', {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify(data),
    });
  });

  it('updateProblema PUTs the diff', async () => {
    await ops.updateProblema(7, { estado: 'resuelto' });
    expect(mockApi).toHaveBeenCalledWith('/api/v1/problemas/7', {
      service: 'gateway',
      method: 'PUT',
      body: JSON.stringify({ estado: 'resuelto' }),
    });
  });

  it('fetchReincidentes omits qs by default', async () => {
    await ops.fetchReincidentes();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/problemas/reincidentes', {
      service: 'gateway',
    });
  });

  it('fetchReincidentes serializes dias + min_correctivas', async () => {
    await ops.fetchReincidentes({ dias: 30, min_correctivas: 2 });
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/problemas/reincidentes?dias=30&min_correctivas=2',
      { service: 'gateway' },
    );
  });

  it('fetchProblemasResumen hits /problemas/resumen', async () => {
    await ops.fetchProblemasResumen();
    expect(mockApi).toHaveBeenCalledWith('/api/v1/problemas/resumen', {
      service: 'gateway',
    });
  });
});
