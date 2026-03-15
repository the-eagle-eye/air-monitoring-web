interface RiskBadgeProps {
  level: 'alta' | 'media' | 'baja';
}

const RISK_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  alta: { bg: 'bg-red-100', text: 'text-red-800', label: 'Alta' },
  media: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Media' },
  baja: { bg: 'bg-green-100', text: 'text-green-800', label: 'Baja' },
};

export default function RiskBadge({ level }: RiskBadgeProps) {
  const style = RISK_STYLES[level] ?? RISK_STYLES.baja;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}
