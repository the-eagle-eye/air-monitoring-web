/**
 * Sensor value extraction that survives the iot-service schema migration.
 *
 * Before migration 004, iot-service returned sensor readings as flat lowercase
 * fields on the reading row:
 *   { so2_ppb: 2.5, box_temp: 45, ... }
 *
 * After migration 004, sensors live in a JSONB column with mixed-case keys
 * that mirror the Thermo analyzer's native output:
 *   { sensors: { SO2_ppb: 2.5, Box_Temp: 45, UVLampIntensity: 97, ... } }
 *
 * This helper accepts a reading in either shape and returns a normalized
 * number|null. UI components use this so the frontend doesn't have to know
 * which schema is on the wire.
 */

import type { LecturaIoT } from '@/types/lectura';

// Maps the frontend's canonical snake_case field name to its JSONB
// counterpart (Thermo native mixed case).
const SNAKE_TO_JSONB: Record<string, string> = {
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

function coerceNumber(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

/** Return the sensor's numeric value from a reading, whichever shape it uses. */
export function readSensor(
  item: Partial<LecturaIoT> | undefined | null,
  snakeKey: string,
): number | null {
  if (!item) return null;

  // Legacy flat field.
  const flat = coerceNumber((item as Record<string, unknown>)[snakeKey]);
  if (flat !== null) return flat;

  // JSONB nested.
  const jsonbKey = SNAKE_TO_JSONB[snakeKey];
  if (jsonbKey && item.sensors) {
    return coerceNumber(item.sensors[jsonbKey]);
  }
  return null;
}

export const SENSOR_SNAKE_KEYS = Object.keys(SNAKE_TO_JSONB) as (keyof typeof SNAKE_TO_JSONB)[];
