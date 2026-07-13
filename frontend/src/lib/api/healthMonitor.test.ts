import {
  fetchHealthReadings,
  fetchHealthState,
  evaluateReading,
  fetchHealthStates,
} from './healthMonitor';
import { apiFetch } from '../api';
import type { HealthDeviceState } from '@/types/healthMonitor';

jest.mock('../api');
const mockApi = apiFetch as jest.MockedFunction<typeof apiFetch>;

beforeEach(() => {
  mockApi.mockReset();
});

describe('healthMonitor API', () => {
  it('fetchHealthReadings defaults limit to 300', async () => {
    mockApi.mockResolvedValueOnce({} as never);
    await fetchHealthReadings('T101');
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/health-monitor/T101/readings?limit=300',
      { service: 'gateway' },
    );
  });

  it('fetchHealthReadings passes an overridden limit', async () => {
    mockApi.mockResolvedValueOnce({} as never);
    await fetchHealthReadings('T101', 50);
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/health-monitor/T101/readings?limit=50',
      { service: 'gateway' },
    );
  });

  it('fetchHealthState hits /health-monitor/{id}/state', async () => {
    mockApi.mockResolvedValueOnce({} as never);
    await fetchHealthState('T101');
    expect(mockApi).toHaveBeenCalledWith('/api/v1/health-monitor/T101/state', {
      service: 'gateway',
    });
  });

  it('evaluateReading POSTs the reading as JSON', async () => {
    mockApi.mockResolvedValueOnce({} as never);
    const reading = {
      device_id: 'T101',
      timestamp: '2026-07-12T00:00:00Z',
      so2_ppb: 12,
      valido: 1,
    };
    await evaluateReading(reading);
    expect(mockApi).toHaveBeenCalledWith('/api/v1/health-monitor/evaluate', {
      service: 'gateway',
      method: 'POST',
      body: JSON.stringify(reading),
    });
  });

  describe('fetchHealthStates', () => {
    const sano: HealthDeviceState = {
      device_id: 'T101',
      health_state: 'SANO',
      last_recon_error: null,
      theta: null,
      hours_since_prev: null,
      updated_at: '2026-07-12T00:00:00Z',
    };

    it('fans out fetchHealthState calls and returns a map', async () => {
      mockApi
        .mockResolvedValueOnce(sano as never)
        .mockResolvedValueOnce({ ...sano, device_id: 'T102' } as never);
      const map = await fetchHealthStates(['T101', 'T102']);
      expect(map).toEqual({
        T101: sano,
        T102: { ...sano, device_id: 'T102' },
      });
    });

    it('coerces per-equipo failures to null (tolerates 404 SIN_DATOS)', async () => {
      mockApi
        .mockResolvedValueOnce(sano as never)
        .mockRejectedValueOnce(new Error('HTTP 404'));
      const map = await fetchHealthStates(['T101', 'T999']);
      expect(map).toEqual({ T101: sano, T999: null });
    });

    it('returns {} for an empty device list', async () => {
      await expect(fetchHealthStates([])).resolves.toEqual({});
      expect(mockApi).not.toHaveBeenCalled();
    });
  });
});
