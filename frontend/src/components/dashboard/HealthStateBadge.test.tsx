import { render, screen } from '@testing-library/react';
import HealthStateBadge from './HealthStateBadge';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';
import type { HealthState } from '@/types/healthMonitor';

const STATES: HealthState[] = [
  'SANO',
  'OBSERVADO',
  'EN_RIESGO',
  'CRITICO',
  'SIN_DATOS',
];

describe('HealthStateBadge', () => {
  it.each(STATES)('renders the label configured for %s', (state) => {
    render(<HealthStateBadge state={state} />);
    expect(
      screen.getByText(HEALTH_STATE_CONFIG[state].label),
    ).toBeInTheDocument();
  });

  it('colors the badge with the state color', () => {
    render(<HealthStateBadge state="CRITICO" />);
    const el = screen.getByText(HEALTH_STATE_CONFIG.CRITICO.label);
    // color is applied via inline style (hex + alpha suffix on bg)
    expect(el).toHaveStyle({ color: HEALTH_STATE_CONFIG.CRITICO.color });
  });

  it('applies small padding classes when size="sm"', () => {
    render(<HealthStateBadge state="SANO" size="sm" />);
    const el = screen.getByText(HEALTH_STATE_CONFIG.SANO.label);
    expect(el.className).toContain('text-xs');
  });

  it('applies medium padding classes by default', () => {
    render(<HealthStateBadge state="SANO" />);
    const el = screen.getByText(HEALTH_STATE_CONFIG.SANO.label);
    expect(el.className).toContain('text-sm');
  });
});
