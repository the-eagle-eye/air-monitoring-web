'use client';

import { useEffect, useState, useCallback } from 'react';
import { usePolling } from '@/hooks/usePolling';
import Link from 'next/link';
import { fetchEquipos } from '@/lib/api/lecturas';
import { fetchIncidencias, createIncidencia } from '@/lib/api/ops';
import IncidenciaForm from '@/components/incidencias/IncidenciaForm';
import DataTable from '@/components/ui/DataTable';
import StatusBadge from '@/components/ui/StatusBadge';
import Badge from '@/components/ui/Badge';
import type { Equipo } from '@/types/lectura';
import type { Incidencia } from '@/types/ops';

const PRIORIDAD_VARIANT: Record<string, 'danger' | 'warning' | 'success'> = {
  alta: 'danger',
  media: 'warning',
  baja: 'success',
};

export default function IncidenciasPage() {
  const [equipos, setEquipos] = useState<Equipo[]>([]);
  const [incidencias, setIncidencias] = useState<Incidencia[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // Filters
  const [filterDevice, setFilterDevice] = useState('');
  const [filterEstado, setFilterEstado] = useState('');

  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const pageSize = 50;

  const loadData = useCallback(
    (silent = false) => {
      if (!silent) setLoading(true);
      fetchIncidencias({
        device_id: filterDevice || undefined,
        tipo: 'correctiva',
        estado: filterEstado || undefined,
        page,
        page_size: pageSize,
      })
        .then((res) => {
          setIncidencias(res.items);
          setTotal(res.total);
          setLastUpdated(new Date());
        })
        .catch((err) => {
          if (!silent) setError(err.message);
        })
        .finally(() => {
          if (!silent) setLoading(false);
        });
    },
    [filterDevice, filterEstado, page],
  );

  useEffect(() => {
    fetchEquipos()
      .then(setEquipos)
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  usePolling(() => loadData(true), 30_000);

  async function handleCreate(data: Parameters<typeof createIncidencia>[0]) {
    await createIncidencia(data);
    setShowForm(false);
    setPage(1);
    loadData(false);
  }

  const totalPages = Math.ceil(total / pageSize);

  const columns = [
    { key: 'id', header: 'ID' },
    { key: 'device_id', header: 'Equipo' },
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
          label={
            item.prioridad.charAt(0).toUpperCase() + item.prioridad.slice(1)
          }
          variant={PRIORIDAD_VARIANT[item.prioridad] ?? 'default'}
        />
      ),
    },
    {
      key: 'descripcion',
      header: 'Descripcion',
      render: (item: Incidencia) =>
        item.descripcion
          ? item.descripcion.length > 50
            ? item.descripcion.slice(0, 50) + '...'
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
      header: 'Acciones',
      render: (item: Incidencia) => (
        <div className="flex gap-2">
          <Link
            href={`/incidencias/${item.id}`}
            className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400"
          >
            Ver
          </Link>
          {item.estado !== 'finalizado' && item.estado !== 'cancelado' && (
            <Link
              href={`/incidencias/${item.id}?mode=edit`}
              className="rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400"
            >
              Editar
            </Link>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
            Incidencias Correctivas
          </h1>
          {lastUpdated && (
            <span className="text-xs text-zinc-400">
              Actualizado: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {showForm ? 'Cancelar' : 'Nueva Incidencia'}
        </button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
          <IncidenciaForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          value={filterDevice}
          onChange={(e) => {
            setFilterDevice(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        >
          <option value="">Todos los equipos</option>
          {equipos.map((eq) => (
            <option key={eq.device_id} value={eq.device_id}>
              {eq.device_id}
            </option>
          ))}
        </select>

        <select
          value={filterEstado}
          onChange={(e) => {
            setFilterEstado(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        >
          <option value="">Todos los estados</option>
          <option value="pendiente">Pendiente</option>
          <option value="en_ejecucion">En Ejecucion</option>
          <option value="finalizado">Finalizado</option>
          <option value="cancelado">Cancelado</option>
        </select>

        <span className="text-sm text-zinc-500">{total} resultados</span>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-zinc-400">Cargando...</div>
      ) : (
        <DataTable
          columns={columns}
          data={incidencias}
          keyExtractor={(i) => i.id}
        />
      )}

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-md bg-zinc-100 px-3 py-1.5 text-sm disabled:opacity-50 dark:bg-zinc-800"
          >
            Anterior
          </button>
          <span className="text-sm text-zinc-500">
            Pagina {page} de {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-md bg-zinc-100 px-3 py-1.5 text-sm disabled:opacity-50 dark:bg-zinc-800"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
}
