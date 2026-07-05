import type { HealthState } from '@/types/healthMonitor';
import { HEALTH_STATE_CONFIG } from '@/types/healthMonitor';

interface HealthStateBadgeProps {
  state: HealthState;
  size?: 'sm' | 'md';
}

// Badge de estado de salud predictiva (ensemble). Reutilizable en tarjetas y detalle.
export default function HealthStateBadge({
  state,
  size = 'md',
}: HealthStateBadgeProps) {
  const cfg = HEALTH_STATE_CONFIG[state];
  const pad = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${pad}`}
      style={{ backgroundColor: `${cfg.color}22`, color: cfg.color }}
    >
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: cfg.color }}
      />
      {cfg.label}
    </span>
  );
}
