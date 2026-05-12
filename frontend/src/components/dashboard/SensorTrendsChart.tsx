'use client';

import dynamic from 'next/dynamic';
import type { LecturaIoT } from '@/types/lectura';

const SENSOR_LINES = [
  { key: 'so2_ppb', name: 'SO2 (ppb)', color: '#8b5cf6' },
  { key: 'h2s_ppb', name: 'H2S (ppb)', color: '#06b6d4' },
  { key: 'reaction_temp', name: 'Temp. Reaccion', color: '#ef4444' },
  { key: 'box_temp', name: 'Temp. Caja', color: '#f97316' },
  { key: 'sample_flow', name: 'Flujo Muestra', color: '#22c55e' },
  { key: 'uv_lamp_intensity', name: 'Intensidad UV', color: '#eab308' },
];

function parseUTC(ts: string): Date {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z');
}

function formatTimestamp(ts: string): string {
  const d = parseUTC(ts);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
}

interface ChartContentProps {
  data: Record<string, unknown>[];
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
        ResponsiveContainer,
      } = mod;

      function SensorLineChart({ data }: ChartContentProps) {
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#a1a1aa40" />
              <XAxis
                dataKey="timestamp"
                tick={{ fontSize: 11 }}
                stroke="#a1a1aa"
              />
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
              {SENSOR_LINES.map((sensor) => (
                <Line
                  key={sensor.key}
                  type="monotone"
                  dataKey={sensor.key}
                  name={sensor.name}
                  stroke={sensor.color}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );
      }

      return SensorLineChart;
    }),
  { ssr: false, loading: () => <div className="h-[300px]" /> },
);

interface SensorTrendsChartProps {
  lecturas: LecturaIoT[];
  loading: boolean;
  selectedEquipo: string;
  equipoOptions: { device_id: string; label: string }[];
  onEquipoChange: (deviceId: string) => void;
}

export default function SensorTrendsChart({
  lecturas,
  loading,
  selectedEquipo,
  equipoOptions,
  onEquipoChange,
}: SensorTrendsChartProps) {
  const chartData = lecturas.map((l) => ({
    timestamp: formatTimestamp(l.timestamp_lectura),
    so2_ppb: l.so2_ppb,
    h2s_ppb: l.h2s_ppb,
    reaction_temp: l.reaction_temp,
    box_temp: l.box_temp,
    sample_flow: l.sample_flow,
    uv_lamp_intensity: l.uv_lamp_intensity,
  }));

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Tendencias de Sensores
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
        <div className="flex h-[300px] items-center justify-center text-sm text-zinc-400">
          Selecciona un equipo para ver tendencias
        </div>
      ) : loading ? (
        <div className="flex h-[300px] items-center justify-center text-sm text-zinc-400">
          Cargando lecturas...
        </div>
      ) : chartData.length === 0 ? (
        <div className="flex h-[300px] items-center justify-center text-sm text-zinc-400">
          Sin lecturas disponibles
        </div>
      ) : (
        <Chart data={chartData} />
      )}
    </div>
  );
}
