'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  fetchIncidencia,
  updateIncidencia,
  submitMantenimiento,
  fetchUsuarios,
} from '@/lib/api/ops';
import StatusBadge from '@/components/ui/StatusBadge';
import Badge from '@/components/ui/Badge';
import type { Incidencia, Usuario, Mantenimiento } from '@/types/ops';

export default function IncidenciaDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [incidencia, setIncidencia] = useState<Incidencia | null>(null);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [editEstado, setEditEstado] = useState('');
  const [editResponsable, setEditResponsable] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Mantenimiento form
  const [mtoDiagnostico, setMtoDiagnostico] = useState('');
  const [mtoAcciones, setMtoAcciones] = useState('');
  const [mtoConclusion, setMtoConclusion] = useState('');
  const [mtoSubmitting, setMtoSubmitting] = useState(false);
  const [mtoSubmitted, setMtoSubmitted] = useState(false);
  const [mtoError, setMtoError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchIncidencia(id), fetchUsuarios()])
      .then(([inc, users]) => {
        setIncidencia(inc);
        setEditEstado(inc.estado);
        setEditResponsable(inc.responsable_id ? String(inc.responsable_id) : '');
        setUsuarios(users);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleSave() {
    if (!incidencia) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const updated = await updateIncidencia(id, {
        estado: editEstado !== incidencia.estado ? editEstado : undefined,
        responsable_id: editResponsable ? Number(editResponsable) : undefined,
      });
      setIncidencia(updated);
      setSaveMsg('Cambios guardados');
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmitMantenimiento(e: React.FormEvent) {
    e.preventDefault();
    setMtoSubmitting(true);
    setMtoError(null);
    try {
      await submitMantenimiento(id, {
        diagnostico: mtoDiagnostico || undefined,
        acciones_realizadas: mtoAcciones || undefined,
        conclusion: mtoConclusion || undefined,
      });
      setMtoSubmitted(true);
    } catch (err) {
      setMtoError(err instanceof Error ? err.message : 'Error al registrar');
    } finally {
      setMtoSubmitting(false);
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-4xl px-4 py-12 text-center text-zinc-400">Cargando...</div>;
  }

  if (error || !incidencia) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error ?? 'Incidencia no encontrada'}
        </div>
      </div>
    );
  }

  const responsable = usuarios.find((u) => u.id === incidencia.responsable_id);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Incidencia #{incidencia.id}
        </h1>
        <div className="flex gap-2">
          <Link
            href={`/equipos/${incidencia.device_id}`}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
          >
            Ver Equipo
          </Link>
          <button
            onClick={() => router.back()}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
          >
            Volver
          </button>
        </div>
      </div>

      {/* Datos de la incidencia */}
      <div className="mb-8 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Equipo</dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {incidencia.device_id}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Tipo</dt>
            <dd className="mt-0.5">
              <Badge
                label={incidencia.tipo === 'correctiva' ? 'Correctiva' : 'Calibracion'}
                variant={incidencia.tipo === 'correctiva' ? 'danger' : 'info'}
              />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Prioridad</dt>
            <dd className="mt-0.5">
              <Badge
                label={incidencia.prioridad.charAt(0).toUpperCase() + incidencia.prioridad.slice(1)}
                variant={
                  incidencia.prioridad === 'alta'
                    ? 'danger'
                    : incidencia.prioridad === 'media'
                      ? 'warning'
                      : 'success'
                }
              />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Responsable</dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {responsable ? `${responsable.nombre} ${responsable.apellido}` : 'Sin asignar'}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Creada</dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {new Date(incidencia.created_at).toLocaleString()}
            </dd>
          </div>
          {incidencia.updated_at && (
            <div>
              <dt className="text-xs font-medium uppercase text-zinc-500">Actualizada</dt>
              <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
                {new Date(incidencia.updated_at).toLocaleString()}
              </dd>
            </div>
          )}
        </div>

        {incidencia.descripcion && (
          <div className="mb-4">
            <dt className="text-xs font-medium uppercase text-zinc-500">Descripcion</dt>
            <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
              {incidencia.descripcion}
            </dd>
          </div>
        )}

        {/* Editar estado y responsable */}
        <div className="border-t border-zinc-200 pt-4 dark:border-zinc-700">
          <h3 className="mb-3 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            Actualizar
          </h3>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs text-zinc-500">Estado</label>
              <select
                value={editEstado}
                onChange={(e) => setEditEstado(e.target.value)}
                className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              >
                <option value="pendiente">Pendiente</option>
                <option value="en_ejecucion">En Ejecucion</option>
                <option value="finalizado">Finalizado</option>
                <option value="cancelado">Cancelado</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-500">Responsable</label>
              <select
                value={editResponsable}
                onChange={(e) => setEditResponsable(e.target.value)}
                className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              >
                <option value="">Sin asignar</option>
                {usuarios.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.nombre} {u.apellido}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Guardando...' : 'Guardar Cambios'}
            </button>
            {saveMsg && (
              <span className="text-sm text-green-600">{saveMsg}</span>
            )}
          </div>
        </div>
      </div>

      {/* Seccion Mantenimiento Correctivo */}
      {incidencia.tipo === 'correctiva' && (
        <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
          <h2 className="mb-4 text-lg font-bold text-zinc-900 dark:text-white">
            Mantenimiento Correctivo
          </h2>

          {mtoSubmitted ? (
            <div className="rounded-md bg-green-50 p-4 text-sm text-green-700">
              Mantenimiento registrado exitosamente.
            </div>
          ) : (
            <form onSubmit={handleSubmitMantenimiento} className="space-y-4">
              {mtoError && (
                <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                  {mtoError}
                </div>
              )}
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Diagnostico
                </label>
                <textarea
                  value={mtoDiagnostico}
                  onChange={(e) => setMtoDiagnostico(e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Acciones Realizadas
                </label>
                <textarea
                  value={mtoAcciones}
                  onChange={(e) => setMtoAcciones(e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Conclusion
                </label>
                <textarea
                  value={mtoConclusion}
                  onChange={(e) => setMtoConclusion(e.target.value)}
                  rows={2}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <button
                type="submit"
                disabled={mtoSubmitting}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {mtoSubmitting ? 'Registrando...' : 'Registrar Mantenimiento'}
              </button>
            </form>
          )}
        </div>
      )}

      {/* Link a calibracion si tipo=calibracion */}
      {incidencia.tipo === 'calibracion' && (
        <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
          <h2 className="mb-3 text-lg font-bold text-zinc-900 dark:text-white">
            Calibracion Asociada
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Esta incidencia es de tipo calibracion. Puede ver y gestionar las calibraciones desde la{' '}
            <Link
              href={`/calibraciones?device_id=${incidencia.device_id}`}
              className="font-medium text-blue-600 hover:underline"
            >
              pagina de calibraciones
            </Link>.
          </p>
        </div>
      )}
    </div>
  );
}
