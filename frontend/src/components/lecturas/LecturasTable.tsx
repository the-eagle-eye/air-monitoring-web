'use client';

import DataTable from '@/components/ui/DataTable';
import { readSensor } from '@/lib/sensorFields';
import type { LecturaIoT } from '@/types/lectura';

interface LecturasTableProps {
  lecturas: LecturaIoT[];
}

const SENSOR_COLUMNS = [
  { key: 'so2_ppb', header: 'SO₂ (ppb)' },
  { key: 'h2s_ppb', header: 'H₂S (ppb)' },
  { key: 'reaction_temp', header: 'Reaction T°' },
  { key: 'izs_temp', header: 'IZS T°' },
  { key: 'pmt_temp', header: 'PMT T°' },
  { key: 'sample_flow', header: 'Sample Flow' },
  { key: 'pressure', header: 'Pressure' },
  { key: 'uv_lamp_intensity', header: 'UV Lamp' },
  { key: 'box_temp', header: 'Box T°' },
  { key: 'hvps_v', header: 'HVPS (V)' },
  { key: 'conv_temp', header: 'Conv T°' },
  { key: 'ozone_flow', header: 'Ozone Flow' },
];

function formatValue(val: number | null): string {
  if (val === null || val === undefined) return '—';
  return val.toFixed(2);
}

export default function LecturasTable({ lecturas }: LecturasTableProps) {
  const columns = [
    {
      key: 'equipo_device_id',
      header: 'Equipo',
    },
    {
      key: 'timestamp_lectura',
      header: 'Timestamp',
      render: (item: LecturaIoT) =>
        new Date(
          item.timestamp_lectura.endsWith('Z')
            ? item.timestamp_lectura
            : item.timestamp_lectura + 'Z',
        ).toLocaleString(),
    },
    ...SENSOR_COLUMNS.map((col) => ({
      ...col,
      render: (item: LecturaIoT) => formatValue(readSensor(item, col.key)),
    })),
  ];

  return (
    <DataTable columns={columns} data={lecturas} keyExtractor={(l) => l.id} />
  );
}
