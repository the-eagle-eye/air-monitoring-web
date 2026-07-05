'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  fetchProblema,
  fetchProblemaIncidencias,
  updateProblema,
} from '@/lib/api/ops';
import DataTable from '@/components/ui/DataTable';
import StatusBadge from '@/components/ui/StatusBadge';
import Badge from '@/components/ui/Badge';
import type { Problema, Incidencia } from '@/types/ops';

const ESTADO_VARIANT: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'default'> = {
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

const ESTADOS = ['abierto', 'investigacion', 'resuelto', 'cerrado'];

const PRIORIDAD_VARIANT: Record<string, 'danger' | 'warning' | 'success'> = {
  alta: 'danger',
  media: 'warning',
  baja: 'success',
};

export default function ProblemaDetailPage() {
  const params = useParams();
  const id = Number(params.id);

  const [problema, setProblema] = useState<Problema | null>(null);
  const [incidencias, setIncidencias] = useState<Incidencia[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [editing, setEditing] = useState(false);
  const [estado, setEstado] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [causaRaiz, setCausaRaiz] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const loadData = useCallback(() => {
    if (Number.isNaN(id)) {
      setError('ID invalido.');
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([fetchProblema(id), fetchProblemaIncidencias(id)])
      .then(([prob, incs]) => {
        setProblema(prob);
        setIncidencias(incs);
        setEstado(prob.estado);
        setDescripcion(prob.descripcion ?? '');
        setCausaRaiz(prob.causa_raiz ?? '');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => { loadData(); }, [loadData]);

  function startEdit() {
    if (!problema) return;
    setEstado(problema.estado);
    setDescripcion(problema.descripcion ?? '');
    setCausaRaiz(problema.causa_raiz ?? '');
    setSaveError(null);
    setEditing(true);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await updateProblema(id, {
        estado,
        descripcion: descripcion.trim() || undefined,
        causa_raiz: causaRaiz.trim() || undefined,
      });
      setProblema(updated);
      setEditing(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Error al guardar.');
    } finally {
      setSaving(false);
    }
  }

  const incidenciaColumns = [
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
          label={item.prioridad.charAt(0).toUpperCase() + item.prioridad.slice(1)}
          variant={PRIORIDAD_VARIANT[item.prioridad] ?? 'default'}
        />
      ),
    },
    {
      key: 'acciones',
      header: 'Acciones',
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
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6">
        <Link
          href="/problemas"
          className="text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          &larr; Volver a Problemas
        </Link>
      </div>

      {loading ? (
        <div className="py-12 text-center text-zinc-400">Cargando...</div>
      ) : error ? (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      ) : problema ? (
        <>
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
                {problema.titulo}
              </h1>
              <div className="mt-2 flex items-center gap-3">
                <Badge
                  label={ESTADO_LABEL[problema.estado] ?? problema.estado}
                  variant={ESTADO_VARIANT[problema.estado] ?? 'default'}
                />
                <span className="text-sm text-zinc-500">
                  #{problema.id}
                  {problema.device_id ? ` · Equipo ${problema.device_id}` : ''}
                </span>
              </div>
            </div>
            {!editing && (
              <button
                onClick={startEdit}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Editar
              </button>
            )}
          </div>

          {editing ? (
            <form
              onSubmit={handleSave}
              className="mb-8 space-y-4 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900"
            >
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Estado
                </label>
                <select
                  value={estado}
                  onChange={(e) => setEstado(e.target.value)}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                >
                  {ESTADOS.map((s) => (
                    <option key={s} value={s}>
                      {ESTADO_LABEL[s]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Descripcion
                </label>
                <textarea
                  value={descripcion}
                  onChange={(e) => setDescripcion(e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Causa raiz
                </label>
                <textarea
                  value={causaRaiz}
                  onChange={(e) => setCausaRaiz(e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                  placeholder="Analisis de causa raiz del problema..."
                />
              </div>

              {saveError && (
                <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{saveError}</div>
              )}

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Guardando...' : 'Guardar'}
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-400 dark:hover:bg-zinc-800"
                >
                  Cancelar
                </button>
              </div>
            </form>
          ) : (
            <div className="mb-8 space-y-6 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
              <div>
                <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Descripcion
                </h3>
                <p className="whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
                  {problema.descripcion || '—'}
                </p>
              </div>
              <div>
                <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Causa raiz
                </h3>
                <p className="whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
                  {problema.causa_raiz || '—'}
                </p>
              </div>
            </div>
          )}

          <div>
            <h2 className="mb-3 text-lg font-semibold text-zinc-900 dark:text-white">
              Incidentes vinculados ({incidencias.length})
            </h2>
            <DataTable
              columns={incidenciaColumns}
              data={incidencias}
              keyExtractor={(i) => i.id}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
