'use client';

import dynamic from 'next/dynamic';
import type { RiskDistribution } from '@/types/dashboard';

const RADIAN = Math.PI / 180;

const Chart = dynamic(
  () =>
    import('recharts').then((mod) => {
      const { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } = mod;

      function CustomLabel(props: Record<string, unknown>) {
        const cx = (props.cx as number) ?? 0;
        const cy = (props.cy as number) ?? 0;
        const midAngle = (props.midAngle as number) ?? 0;
        const outerRadius = (props.outerRadius as number) ?? 0;
        const name = (props.name as string) ?? '';
        const percent = (props.percent as number) ?? 0;

        const radius = outerRadius + 25;
        const x = cx + radius * Math.cos(-midAngle * RADIAN);
        const y = cy + radius * Math.sin(-midAngle * RADIAN);

        return (
          <text
            x={x}
            y={y}
            fill="#d4d4d8"
            textAnchor={x > cx ? 'start' : 'end'}
            dominantBaseline="central"
            fontSize={13}
            fontWeight={500}
          >
            {name} ({(percent * 100).toFixed(0)}%)
          </text>
        );
      }

      function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { color: string; value: number }; [k: string]: unknown }> }) {
        if (!active || !payload || !payload.length) return null;
        const entry = payload[0];
        const total = payload.reduce((sum, p) => sum + p.value, 0) || 1;
        const pct = ((entry.value / total) * 100).toFixed(1);
        return (
          <div
            style={{
              background: '#27272a',
              border: '1px solid #52525b',
              borderRadius: 8,
              padding: '8px 12px',
              color: '#f4f4f5',
              fontSize: 13,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
              <span
                style={{
                  display: 'inline-block',
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: entry.payload.color,
                }}
              />
              <strong>{entry.name}</strong>
            </div>
            <div>{entry.value} equipo{entry.value !== 1 ? 's' : ''} ({pct}%)</div>
          </div>
        );
      }

      function RiskPieChart({ data }: { data: RiskDistribution[] }) {
        const filtered = data.filter((d) => d.value > 0);
        const total = filtered.reduce((sum, d) => sum + d.value, 0);

        return (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={filtered}
                cx="50%"
                cy="45%"
                innerRadius={55}
                outerRadius={100}
                dataKey="value"
                nameKey="name"
                paddingAngle={filtered.length > 1 ? 3 : 0}
                strokeWidth={0}
                label={CustomLabel as unknown as boolean}
                labelLine={{ stroke: '#71717a', strokeWidth: 1 }}
              >
                {filtered.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="bottom"
                height={36}
                formatter={(value: string) => {
                  const item = data.find((d) => d.name === value);
                  return (
                    <span style={{ color: '#d4d4d8', fontSize: 13 }}>
                      {value} ({item?.value ?? 0})
                    </span>
                  );
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        );
      }

      return RiskPieChart;
    }),
  { ssr: false, loading: () => <div className="h-[280px]" /> },
);

interface RiskDistributionChartProps {
  data: RiskDistribution[];
}

export default function RiskDistributionChart({
  data,
}: RiskDistributionChartProps) {
  const hasData = data.some((d) => d.value > 0);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        Distribución de Salud
      </h2>
      {!hasData ? (
        <div className="flex h-[280px] items-center justify-center text-sm text-zinc-400">
          Sin datos de salud
        </div>
      ) : (
        <Chart data={data} />
      )}
    </div>
  );
}
