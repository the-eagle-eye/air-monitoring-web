'use client';

import dynamic from 'next/dynamic';
import type { HealthReadingPoint } from '@/types/healthMonitor';

function parseUTC(ts: string): Date {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z');
}

function formatTimestamp(ts: string): string {
  const d = parseUTC(ts);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
}

interface ChartContentProps {
  data: { timestamp: string; recon_error: number | null }[];
  theta: number | null;
}

const Chart = dynamic(
  () =>
    import('recharts').then((mod) => {
      const {
        LineChart,
        Line,
        XAxis,
        YAxis,
        CartesianGrid,
        Tooltip,
        Legend,
        ReferenceLine,
        ResponsiveContainer,
      } = mod;

      function ReconLineChart({ data, theta }: ChartContentProps) {
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#a1a1aa40" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} stroke="#a1a1aa" />
              <YAxis tick={{ fontSize: 11 }} stroke="#a1a1aa" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#18181b',
                  border: '1px solid #3f3f46',
                  borderRadius: '8px',
                  color: '#fafafa',
                  fontSize: 12,
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="recon_error"
                name="Error de reconstrucción"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
                connectNulls
              />
              {theta != null && (
                <ReferenceLine
                  y={theta}
                  stroke="#ef4444"
                  strokeDasharray="6 4"
                  label={{ value: 'θ (umbral)', fill: '#ef4444', fontSize: 11 }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        );
      }

      return ReconLineChart;
    }),
  { ssr: false, loading: () => <div className="h-[300px]" /> },
);

interface ReconErrorChartProps {
  points: HealthReadingPoint[];
  loading?: boolean;
}

// Gráfico de tendencia del error de reconstrucción del ensemble con la línea θ
// (poc-dashboard §3.2). Visible a todos los roles (decisión §7.2).
export default function ReconErrorChart({ points, loading }: ReconErrorChartProps) {
  const theta = points.find((p) => p.theta != null)?.theta ?? null;
  const data = points.map((p) => ({
    timestamp: formatTimestamp(p.timestamp),
    recon_error: p.recon_error,
  }));

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-700 dark:bg-zinc-900">
      <h3 className="mb-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        Error de reconstrucción (salud del equipo)
      </h3>
      <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
        Cuando la línea supera θ y el segundo detector confirma, se emite una
        alerta. Por debajo de θ, operación normal.
      </p>
      {loading ? (
        <div className="h-[300px] animate-pulse rounded bg-zinc-100 dark:bg-zinc-800" />
      ) : data.length === 0 ? (
        <div className="flex h-[300px] items-center justify-center text-sm text-zinc-400">
          Sin datos de salud para este equipo todavía.
        </div>
      ) : (
        <Chart data={data} theta={theta} />
      )}
    </div>
  );
}
