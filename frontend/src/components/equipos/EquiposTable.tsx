'use client';

import Link from 'next/link';
import DataTable from '@/components/ui/DataTable';
import StatusBadge from '@/components/ui/StatusBadge';
import type { Equipo } from '@/types/lectura';

interface EquiposTableProps {
  equipos: Equipo[];
  readOnly?: boolean;
}

export default function EquiposTable({
  equipos,
  readOnly = false,
}: EquiposTableProps) {
  const columns = [
    {
      key: 'nombre',
      header: 'Nombre',
      render: (item: Equipo) => item.nombre ?? item.device_id,
    },
    {
      key: 'device_id',
      header: 'Device ID',
    },
    {
      key: 'serie',
      header: 'Serie',
      render: (item: Equipo) => item.serie ?? '—',
    },
    {
      key: 'ubicacion',
      header: 'Ubicacion',
      render: (item: Equipo) => item.ubicacion ?? '—',
    },
    {
      key: 'parametro_medicion',
      header: 'Parametro',
      render: (item: Equipo) => item.parametro_medicion ?? '—',
    },
    {
      key: 'estado',
      header: 'Estado',
      render: (item: Equipo) => <StatusBadge status={item.estado} />,
    },
    {
      key: 'acciones',
      header: 'Acciones',
      render: (item: Equipo) => (
        <div className="flex items-center gap-2">
          <Link
            href={`/equipos/${item.device_id}`}
            className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400"
          >
            Ver
          </Link>
          {!readOnly && (
            <>
              <Link
                href={`/equipos/${item.device_id}?mode=edit`}
                className="rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400"
              >
                Editar
              </Link>
              <button
                disabled
                title="Proximamente"
                className="cursor-not-allowed rounded bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-400 dark:bg-zinc-800"
              >
                Eliminar
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <DataTable columns={columns} data={equipos} keyExtractor={(e) => e.id} />
  );
}
