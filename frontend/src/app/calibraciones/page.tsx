'use client';

import { useEffect, useState, useCallback } from 'react';
import { usePolling } from '@/hooks/usePolling';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { fetchEquipos } from '@/lib/api/lecturas';
import {
  fetchCalibracionesOps,
  createCalibracion,
  fetchProveedores,
} from '@/lib/api/ops';
import DataTable from '@/components/ui/DataTable';
import StatusBadge from '@/components/ui/StatusBadge';
import type { Equipo } from '@/types/lectura';
import type { CalibracionOps, Proveedor } from '@/types/ops';

export default function CalibracionesPage() {
  const { user } = useAuth();
  // El técnico solo COMPLETA sus calibraciones asignadas; no crea nuevas.
  const canCrear = user?.rol === 'coordinador' || user?.rol === 'administrador';
  const [equipos, setEquipos] = useState<Equipo[]>([]);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [calibraciones, setCalibraciones] = useState<CalibracionOps[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [filterDevice, setFilterDevice] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const pageSize = 50;

  // Create form
  const [formDevice, setFormDevice] = useState('');
  const [formNota, setFormNota] = useState('');
  const [formProveedor, setFormProveedor] = useState('');
  const [creating, setCreating] = useState(false);

  const loadData = useCallback(
    (silent = false) => {
      if (!silent) setLoading(true);
      fetchCalibracionesOps({
        device_id: filterDevice || undefined,
        page,
        page_size: pageSize,
      })
        .then((res) => {
          setCalibraciones(res.items);
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
    [filterDevice, page],
  );

  useEffect(() => {
    fetchEquipos()
      .then((eqs) => {
        setEquipos(eqs);
        if (eqs.length > 0) setFormDevice(eqs[0].device_id);
      })
      .catch(() => {});
    fetchProveedores()
      .then(setProveedores)
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  usePolling(() => loadData(true), 30_000);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createCalibracion({
        device_id: formDevice,
        nota: formNota || undefined,
        proveedor_id: formProveedor ? Number(formProveedor) : undefined,
      });
      setShowForm(false);
      setFormNota('');
      setFormProveedor('');
      setPage(1);
      loadData(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear');
    } finally {
      setCreating(false);
    }
  }

  const totalPages = Math.ceil(total / pageSize);

  const proveedorMap = Object.fromEntries(
    proveedores.map((p) => [p.id, p.nombre]),
  );

  const columns = [
    { key: 'id', header: 'ID' },
    { key: 'device_id', header: 'Equipo' },
    {
      key: 'estado',
      header: 'Estado',
      render: (item: CalibracionOps) => <StatusBadge status={item.estado} />,
    },
    {
      key: 'fecha_calibracion',
      header: 'Fecha Calibracion',
      render: (item: CalibracionOps) =>
        item.fecha_calibracion
          ? new Date(item.fecha_calibracion).toLocaleDateString()
          : '—',
    },
    {
      key: 'nota',
      header: 'Nota',
      render: (item: CalibracionOps) =>
        item.nota
          ? item.nota.length > 40
            ? item.nota.slice(0, 40) + '...'
            : item.nota
          : '—',
    },
    {
      key: 'certificado_url',
      header: 'Certificado',
      render: (item: CalibracionOps) =>
        item.certificado_url ? (
          <a
            href={item.certificado_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-blue-600 hover:underline"
          >
            Ver
          </a>
        ) : (
          '—'
        ),
    },
    {
      key: 'proveedor_id',
      header: 'Proveedor',
      render: (item: CalibracionOps) =>
        item.proveedor_id
          ? (proveedorMap[item.proveedor_id] ?? `#${item.proveedor_id}`)
          : '—',
    },
    {
      key: 'created_at',
      header: 'Creada',
      render: (item: CalibracionOps) =>
        new Date(item.created_at).toLocaleDateString(),
    },
    {
      key: 'acciones',
      header: 'Acciones',
      render: (item: CalibracionOps) => (
        <div className="flex gap-2">
          <Link
            href={`/calibraciones/${item.id}`}
            className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400"
          >
            Ver
          </Link>
          {item.estado !== 'completada' && (
            <Link
              href={`/calibraciones/${item.id}?mode=edit`}
              className="rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400"
            >
              Editar
            </Link>
          )}
          {item.incidencia_id && (
            <Link
              href={`/incidencias/${item.incidencia_id}`}
              className="rounded bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400"
            >
              Incidencia
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
            Calibraciones
          </h1>
          {lastUpdated && (
            <span className="text-xs text-zinc-400">
              Actualizado: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        {canCrear && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {showForm ? 'Cancelar' : 'Nueva Calibracion'}
          </button>
        )}
      </div>

      {canCrear && showForm && (
        <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
          <form
            onSubmit={handleCreate}
            className="flex flex-wrap items-end gap-4"
          >
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Equipo
              </label>
              <select
                value={formDevice}
                onChange={(e) => setFormDevice(e.target.value)}
                required
                className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              >
                {equipos.map((eq) => (
                  <option key={eq.device_id} value={eq.device_id}>
                    {eq.device_id} — {eq.nombre ?? 'Sin nombre'}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Proveedor
              </label>
              <select
                value={formProveedor}
                onChange={(e) => setFormProveedor(e.target.value)}
                className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              >
                <option value="">Sin proveedor</option>
                {proveedores.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Nota
              </label>
              <input
                type="text"
                value={formNota}
                onChange={(e) => setFormNota(e.target.value)}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              />
            </div>
            <button
              type="submit"
              disabled={creating}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? 'Creando...' : 'Crear'}
            </button>
          </form>
        </div>
      )}

      <div className="mb-4 flex items-center gap-3">
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
          data={calibraciones}
          keyExtractor={(c) => c.id}
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
