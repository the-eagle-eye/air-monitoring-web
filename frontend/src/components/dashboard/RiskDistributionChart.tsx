'use client';

import dynamic from 'next/dynamic';
import type { RiskDistribution } from '@/types/dashboard';

const Chart = dynamic(
  () =>
    import('recharts').then((mod) => {
      const { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } = mod;

      function RiskPieChart({ data }: { data: RiskDistribution[] }) {
        return (
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={90}
                dataKey="value"
                nameKey="name"
                label={({ name, value }: { name?: string; value?: number }) =>
                  `${name ?? ''}: ${value ?? 0}`
                }
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );
      }

      return RiskPieChart;
    }),
  { ssr: false, loading: () => <div className="h-[250px]" /> },
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
        Distribucion de Riesgo
      </h2>
      {!hasData ? (
        <div className="flex h-[250px] items-center justify-center text-sm text-zinc-400">
          Sin datos de prediccion
        </div>
      ) : (
        <Chart data={data} />
      )}
    </div>
  );
}
