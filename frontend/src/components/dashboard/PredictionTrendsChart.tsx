'use client';

import dynamic from 'next/dynamic';
import type { Prediccion } from '@/types/prediccion';

function parseUTC(ts: string): Date {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z');
}

function formatTimestamp(ts: string): string {
  const d = parseUTC(ts);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
}

interface ChartContentProps {
  data: { timestamp: string; rul: number; failProb: number }[];
}

const Chart = dynamic(
  () =>
    import('recharts').then((mod) => {
      const {
        ComposedChart,
        Line,
        XAxis,
        YAxis,
        CartesianGrid,
        Tooltip,
        Legend,
        ResponsiveContainer,
        ReferenceLine,
      } = mod;

      function PredictionChart({ data }: ChartContentProps) {
        const maxRul = Math.max(...data.map((d) => d.rul), 80);
        const showDots = data.length <= 10;
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#a1a1aa40" />
              <XAxis
                dataKey="timestamp"
                tick={{ fontSize: 11 }}
                stroke="#a1a1aa"
              />
              <YAxis
                yAxisId="left"
                domain={[0, maxRul]}
                tick={{ fontSize: 11 }}
                stroke="#06b6d4"
                label={{
                  value: 'RUL (dias)',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: 12, fill: '#06b6d4' },
                }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                stroke="#ef4444"
                label={{
                  value: 'Prob. Falla (%)',
                  angle: 90,
                  position: 'insideRight',
                  style: { fontSize: 12, fill: '#ef4444' },
                }}
              />
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
              <ReferenceLine
                yAxisId="left"
                y={30}
                stroke="#ef4444"
                strokeDasharray="6 3"
                label={{ value: 'Critico', position: 'left', fill: '#ef4444', fontSize: 11 }}
              />
              <ReferenceLine
                yAxisId="left"
                y={60}
                stroke="#eab308"
                strokeDasharray="6 3"
                label={{ value: 'Precaucion', position: 'left', fill: '#eab308', fontSize: 11 }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="rul"
                name="RUL (dias)"
                stroke="#06b6d4"
                strokeWidth={2}
                dot={showDots ? { r: 4, fill: '#06b6d4' } : false}
                connectNulls
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="failProb"
                name="Prob. Falla (%)"
                stroke="#ef4444"
                strokeWidth={2}
                dot={showDots ? { r: 4, fill: '#ef4444' } : false}
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }

      return PredictionChart;
    }),
  { ssr: false, loading: () => <div className="h-[350px]" /> },
);

interface PredictionTrendsChartProps {
  predicciones: Prediccion[];
  loading: boolean;
  selectedEquipo: string;
  equipoOptions: { device_id: string; label: string }[];
  onEquipoChange: (deviceId: string) => void;
}

export default function PredictionTrendsChart({
  predicciones,
  loading,
  selectedEquipo,
  equipoOptions,
  onEquipoChange,
}: PredictionTrendsChartProps) {
  const chartData = [...predicciones]
    .sort(
      (a, b) =>
        parseUTC(a.prediction_timestamp).getTime() -
        parseUTC(b.prediction_timestamp).getTime(),
    )
    .map((p) => ({
      timestamp: formatTimestamp(p.prediction_timestamp),
      rul: p.remaining_useful_life_days,
      failProb: Math.round(p.failure_probability * 100),
    }));

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Tendencia de Predicciones
        </h2>
        <select
          value={selectedEquipo}
          onChange={(e) => onEquipoChange(e.target.value)}
          className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        >
          <option value="">Seleccionar equipo</option>
          {equipoOptions.map((eq) => (
            <option key={eq.device_id} value={eq.device_id}>
              {eq.label}
            </option>
          ))}
        </select>
      </div>

      {!selectedEquipo ? (
        <div className="flex h-[350px] items-center justify-center text-sm text-zinc-400">
          Selecciona un equipo para ver tendencias de prediccion
        </div>
      ) : loading ? (
        <div className="flex h-[350px] items-center justify-center text-sm text-zinc-400">
          Cargando predicciones...
        </div>
      ) : chartData.length === 0 ? (
        <div className="flex h-[350px] items-center justify-center text-sm text-zinc-400">
          Sin predicciones disponibles
        </div>
      ) : (
        <>
          {chartData.length < 3 && (
            <p className="mb-2 text-center text-xs text-zinc-500">
              Se necesitan mas predicciones para visualizar una tendencia clara.
              Ejecuta predicciones periodicamente desde la seccion Predicciones.
            </p>
          )}
          <Chart data={chartData} />
        </>
      )}
    </div>
  );
}
