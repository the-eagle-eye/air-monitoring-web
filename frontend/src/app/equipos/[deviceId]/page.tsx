'use client';

import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchEquipo, updateEquipo } from '@/lib/api/lecturas';
import { fetchIncidencias } from '@/lib/api/ops';
import EquipoForm from '@/components/equipos/EquipoForm';
import DataTable from '@/components/ui/DataTable';
import StatusBadge from '@/components/ui/StatusBadge';
import Badge from '@/components/ui/Badge';
import type { Equipo } from '@/types/lectura';
import type { Incidencia } from '@/types/ops';

function EquipoDetail({ equipo }: { equipo: Equipo }) {
  const fields = [
    { label: 'Device ID', value: equipo.device_id },
    { label: 'Nombre', value: equipo.nombre },
    { label: 'Tipo', value: equipo.tipo },
    { label: 'Ubicacion', value: equipo.ubicacion },
    { label: 'Serie', value: equipo.serie },
    { label: 'Marca', value: equipo.marca },
    { label: 'Modelo', value: equipo.modelo },
    { label: 'Parametro', value: equipo.parametro_medicion },
    { label: 'Rango', value: equipo.rango_medicion },
    { label: 'Estado', value: equipo.estado },
    { label: 'Fecha Ingreso', value: equipo.fecha_ingreso },
    { label: 'Fecha Registro', value: new Date(equipo.fecha_registro).toLocaleDateString() },
  ];

  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-3">
      {fields.map((f) => (
        <div key={f.label}>
          <dt className="text-xs font-medium uppercase text-zinc-500 dark:text-zinc-400">
            {f.label}
          </dt>
          <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
            {f.value ?? '—'}
          </dd>
        </div>
      ))}
    </div>
  );
}

const PRIORIDAD_VARIANT: Record<string, 'danger' | 'warning' | 'success'> = {
  alta: 'danger',
  media: 'warning',
  baja: 'success',
};

function HistorialTable({
  title,
  incidencias,
}: {
  title: string;
  incidencias: Incidencia[];
}) {
  const columns = [
    { key: 'id', header: 'ID' },
    {
      key: 'estado',
      header: 'Estado',
      render: (item: Incidencia) => <StatusBadge status={item.estado} />,
    },
    {
      key: 'prioridad',
      header: 'Prioridad',
      render: (item: Incidencia) => (
        <Badge
          label={item.prioridad.charAt(0).toUpperCase() + item.prioridad.slice(1)}
          variant={PRIORIDAD_VARIANT[item.prioridad] ?? 'default'}
        />
      ),
    },
    {
      key: 'descripcion',
      header: 'Descripcion',
      render: (item: Incidencia) =>
        item.descripcion
          ? item.descripcion.length > 60
            ? item.descripcion.slice(0, 60) + '...'
            : item.descripcion
          : '—',
    },
    {
      key: 'created_at',
      header: 'Fecha',
      render: (item: Incidencia) =>
        new Date(item.created_at).toLocaleDateString(),
    },
    {
      key: 'acciones',
      header: 'Accion',
      render: (item: Incidencia) => (
        <Link
          href={`/incidencias/${item.id}`}
          className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400"
        >
          Ver
        </Link>
      ),
    },
  ];

  return (
    <div>
      <h3 className="mb-3 text-lg font-semibold text-zinc-800 dark:text-zinc-200">
        {title}
      </h3>
      {incidencias.length === 0 ? (
        <p className="text-sm text-zinc-400">No hay registros</p>
      ) : (
        <DataTable
          columns={columns}
          data={incidencias}
          keyExtractor={(i) => i.id}
        />
      )}
    </div>
  );
}

export default function EquipoDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const deviceId = params.deviceId as string;
  const mode = searchParams.get('mode') ?? 'view';

  const [equipo, setEquipo] = useState<Equipo | null>(null);
  const [correctivos, setCorrectivos] = useState<Incidencia[]>([]);
  const [calibraciones, setCalibraciones] = useState<Incidencia[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchEquipo(deviceId),
      fetchIncidencias({ device_id: deviceId, tipo: 'correctiva', page_size: 100 }),
      fetchIncidencias({ device_id: deviceId, tipo: 'calibracion', page_size: 100 }),
    ])
      .then(([eq, corr, cal]) => {
        setEquipo(eq);
        setCorrectivos(corr.items);
        setCalibraciones(cal.items);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [deviceId]);

  async function handleUpdate(data: Record<string, unknown>) {
    await updateEquipo(deviceId, data);
    const updated = await fetchEquipo(deviceId);
    setEquipo(updated);
    router.replace(`/equipos/${deviceId}`);
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 text-center text-zinc-400">
        Cargando...
      </div>
    );
  }

  if (error || !equipo) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error ?? 'Equipo no encontrado'}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Equipo: {equipo.nombre ?? equipo.device_id}
        </h1>
        <div className="flex gap-2">
          {mode === 'view' && (
            <Link
              href={`/equipos/${deviceId}?mode=edit`}
              className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600"
            >
              Editar
            </Link>
          )}
          <Link
            href="/equipos"
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
          >
            Volver
          </Link>
        </div>
      </div>

      <div className="mb-8 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        {mode === 'edit' ? (
          <EquipoForm
            initialData={equipo}
            mode="edit"
            onSubmit={handleUpdate}
            onCancel={() => router.replace(`/equipos/${deviceId}`)}
          />
        ) : (
          <EquipoDetail equipo={equipo} />
        )}
      </div>

      <div className="space-y-8">
        <h2 className="text-xl font-bold text-zinc-900 dark:text-white">
          Historial de Mantenimientos
        </h2>
        <HistorialTable title="Correctivos" incidencias={correctivos} />
        <HistorialTable title="Calibraciones" incidencias={calibraciones} />
      </div>
    </div>
  );
}
