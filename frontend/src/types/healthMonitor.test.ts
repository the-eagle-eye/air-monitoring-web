import { HEALTH_STATE_CONFIG } from './healthMonitor';
import type { HealthState } from './healthMonitor';

const ALL_STATES: HealthState[] = [
  'SANO',
  'OBSERVADO',
  'EN_RIESGO',
  'CRITICO',
  'SIN_DATOS',
];

describe('HEALTH_STATE_CONFIG', () => {
  it('has an entry for every HealthState', () => {
    for (const s of ALL_STATES) {
      expect(HEALTH_STATE_CONFIG[s]).toBeDefined();
    }
  });

  it('exposes a hex color, label, emoji, and isAlert flag for each state', () => {
    for (const s of ALL_STATES) {
      const cfg = HEALTH_STATE_CONFIG[s];
      expect(cfg.color).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(cfg.label.length).toBeGreaterThan(0);
      expect(cfg.emoji.length).toBeGreaterThan(0);
      expect(typeof cfg.isAlert).toBe('boolean');
    }
  });

  it('flags OBSERVADO / EN_RIESGO / CRITICO as alert states', () => {
    expect(HEALTH_STATE_CONFIG.SANO.isAlert).toBe(false);
    expect(HEALTH_STATE_CONFIG.SIN_DATOS.isAlert).toBe(false);
    expect(HEALTH_STATE_CONFIG.OBSERVADO.isAlert).toBe(true);
    expect(HEALTH_STATE_CONFIG.EN_RIESGO.isAlert).toBe(true);
    expect(HEALTH_STATE_CONFIG.CRITICO.isAlert).toBe(true);
  });
});
