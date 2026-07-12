import { readSensor, SENSOR_SNAKE_KEYS } from './sensorFields';
import type { LecturaIoT } from '@/types/lectura';

describe('readSensor', () => {
  it('reads a legacy flat lowercase field', () => {
    const item = { so2_ppb: 2.5 } as Partial<LecturaIoT>;
    expect(readSensor(item, 'so2_ppb')).toBe(2.5);
  });

  it('reads a post-migration JSONB mixed-case field', () => {
    const item = { sensors: { SO2_ppb: 3.1 } } as Partial<LecturaIoT>;
    expect(readSensor(item, 'so2_ppb')).toBe(3.1);
  });

  it('prefers the flat field over the JSONB field when both exist', () => {
    const item = {
      so2_ppb: 1,
      sensors: { SO2_ppb: 99 },
    } as Partial<LecturaIoT>;
    expect(readSensor(item, 'so2_ppb')).toBe(1);
  });

  it('coerces numeric strings to numbers', () => {
    const item = { sensors: { Box_Temp: '45.2' } } as Partial<LecturaIoT>;
    expect(readSensor(item, 'box_temp')).toBe(45.2);
  });

  it('returns null for non-numeric strings', () => {
    const item = { sensors: { Box_Temp: 'n/a' } } as Partial<LecturaIoT>;
    expect(readSensor(item, 'box_temp')).toBeNull();
  });

  it('returns null when the reading is null or undefined', () => {
    expect(readSensor(null, 'so2_ppb')).toBeNull();
    expect(readSensor(undefined, 'so2_ppb')).toBeNull();
  });

  it('returns null when the sensor key is absent in both shapes', () => {
    const item = { sensors: { H2S_ppb: 1 } } as Partial<LecturaIoT>;
    expect(readSensor(item, 'so2_ppb')).toBeNull();
  });

  it('returns null for a non-finite flat value and does not fall through to a wrong key', () => {
    const item = { so2_ppb: NaN } as Partial<LecturaIoT>;
    expect(readSensor(item, 'so2_ppb')).toBeNull();
  });

  it('maps every canonical snake key to its JSONB counterpart', () => {
    // Guards against a half-added sensor: each key must resolve from JSONB.
    for (const key of SENSOR_SNAKE_KEYS) {
      const jsonbShape = { sensors: {} } as LecturaIoT;
      // Build a reading whose JSONB carries this key set to 7.
      const withValue = {
        sensors: { ...buildJsonbFor(key) },
      } as Partial<LecturaIoT>;
      expect(readSensor(jsonbShape, key)).toBeNull();
      expect(readSensor(withValue, key)).toBe(7);
    }
  });
});

// Helper: produce a JSONB object where the mixed-case counterpart of `snakeKey`
// is 7. We import the same mapping indirectly by round-tripping through readSensor
// on a legacy field to discover the value, but simplest is a local mirror.
const MIRROR: Record<string, string> = {
  so2_ppb: 'SO2_ppb',
  h2s_ppb: 'H2S_ppb',
  reaction_temp: 'Reaction_Temp',
  izs_temp: 'IZS_Temp',
  pmt_temp: 'PMT_Temp',
  sample_flow: 'SampleFlow',
  pressure: 'Pressure',
  uv_lamp_intensity: 'UVLampIntensity',
  box_temp: 'Box_Temp',
  hvps_v: 'HVPS_V',
  conv_temp: 'Conv_Temp',
  ozone_flow: 'Ozone_flow',
};

function buildJsonbFor(snakeKey: string): Record<string, number> {
  return { [MIRROR[snakeKey]]: 7 };
}
