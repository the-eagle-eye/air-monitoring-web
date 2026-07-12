'use client';

import { useEffect, useState, useCallback } from 'react';
import { usePolling } from '@/hooks/usePolling';
import Link from 'next/link';
import { fetchProblemas, createProblema } from '@/lib/api/ops';
import DataTable from '@/components/ui/DataTable';
import Badge from '@/components/ui/Badge';
import type { Problema } from '@/types/ops';

const ESTADO_VARIANT: Record<
  string,
  'success' | 'warning' | 'danger' | 'info' | 'default'
> = {
  abierto: 'danger',
  investigacion: 'warning',
  resuelto: 'success',
  cerrado: 'default',
};

const ESTADO_LABEL: Record<string, string> = {
  abierto: 'Abierto',
  investigacion: 'Investigacion',
  resuelto: 'Resuelto',
  cerrado: 'Cerrado',
};

function EstadoBadge({ estado }: { estado: string }) {
  return (
    <Badge
      label={ESTADO_LABEL[estado] ?? estado}
      variant={ESTADO_VARIANT[estado] ?? 'default'}
    />
  );
}

export default function ProblemasPage() {
  const [problemas, setProblemas] = useState<Problema[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [filterEstado, setFilterEstado] = useState('');

  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Form state
  const [titulo, setTitulo] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadData = useCallback(
    (silent = false) => {
      if (!silent) setLoading(true);
      fetchProblemas({ estado: filterEstado || undefined })
        .then((res) => {
          setProblemas(res.items);
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
    [filterEstado],
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  usePolling(() => loadData(true), 30_000);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!titulo.trim()) {
      setFormError('El titulo es obligatorio.');
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await createProblema({
        titulo: titulo.trim(),
        device_id: deviceId.trim() || undefined,
        descripcion: descripcion.trim() || undefined,
      });
      setTitulo('');
      setDeviceId('');
      setDescripcion('');
      setShowForm(false);
      loadData(false);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : 'Error al crear el problema.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  const columns = [
    { key: 'id', header: 'ID' },
    { key: 'titulo', header: 'Titulo' },
    {
      key: 'device_id',
      header: 'Equipo',
      render: (item: Problema) => item.device_id ?? '—',
    },
    {
      key: 'estado',
      header: 'Estado',
      render: (item: Problema) => <EstadoBadge estado={item.estado} />,
    },
    {
      key: 'created_at',
      header: 'Fecha',
      render: (item: Problema) =>
        new Date(item.created_at).toLocaleDateString(),
    },
    {
      key: 'acciones',
      header: 'Acciones',
      render: (item: Problema) => (
        <Link
          href={`/problemas/${item.id}`}
          className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400"
        >
          Ver
        </Link>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
            Gestion de Problemas
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
          {showForm ? 'Cancelar' : 'Nuevo Problema'}
        </button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Titulo *
              </label>
              <input
                type="text"
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
                required
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                placeholder="Ej. Fallas recurrentes del sensor SO2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Equipo (opcional)
              </label>
              <input
                type="text"
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                placeholder="Ej. T101"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Descripcion (opcional)
              </label>
              <textarea
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                placeholder="Descripcion del problema y su contexto..."
              />
            </div>

            {formError && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={submitting}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? 'Guardando...' : 'Crear Problema'}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          value={filterEstado}
          onChange={(e) => setFilterEstado(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        >
          <option value="">Todos los estados</option>
          <option value="abierto">Abierto</option>
          <option value="investigacion">Investigacion</option>
          <option value="resuelto">Resuelto</option>
          <option value="cerrado">Cerrado</option>
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
          data={problemas}
          keyExtractor={(p) => p.id}
        />
      )}
    </div>
  );
}
