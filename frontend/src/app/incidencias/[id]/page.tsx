'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import {
  fetchIncidencia,
  updateIncidencia,
  submitMantenimiento,
  fetchUsuarios,
  fetchRepuestos,
  fetchProblemas,
  linkIncidenciaProblema,
} from '@/lib/api/ops';
import StatusBadge from '@/components/ui/StatusBadge';
import Badge from '@/components/ui/Badge';
import type { Incidencia, Usuario, Repuesto, Problema } from '@/types/ops';

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  return d.toLocaleString('es-PE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export default function IncidenciaDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [incidencia, setIncidencia] = useState<Incidencia | null>(null);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [repuestos, setRepuestos] = useState<Repuesto[]>([]);
  const [problemas, setProblemas] = useState<Problema[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [editResponsable, setEditResponsable] = useState('');

  // Mantenimiento form
  const [mtoDiagnostico, setMtoDiagnostico] = useState('');
  const [mtoAcciones, setMtoAcciones] = useState('');
  const [mtoConclusion, setMtoConclusion] = useState('');
  const [selectedRepuestoIds, setSelectedRepuestoIds] = useState<number[]>([]);
  const [repuestosOpen, setRepuestosOpen] = useState(false);
  const [adjuntos, setAdjuntos] = useState<{ filename: string; file_url: string }[]>([]);

  // Save state
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{ text: string; isError: boolean } | null>(null);

  const repuestosRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([fetchIncidencia(id), fetchUsuarios(), fetchRepuestos()])
      .then(([inc, users, reps]) => {
        setIncidencia(inc);
        setEditResponsable(inc.responsable_id ? String(inc.responsable_id) : '');
        setUsuarios(users);
        setRepuestos(reps);
        fetchProblemas().then((r) => setProblemas(r.items)).catch(() => {});
        // Pre-populate mantenimiento fields if data exists
        if (inc.mantenimiento_correctivo) {
          setMtoDiagnostico(inc.mantenimiento_correctivo.diagnostico ?? '');
          setMtoAcciones(inc.mantenimiento_correctivo.acciones_realizadas ?? '');
          setMtoConclusion(inc.mantenimiento_correctivo.conclusion ?? '');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  // Close repuestos dropdown on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (repuestosRef.current && !repuestosRef.current.contains(e.target as Node)) {
        setRepuestosOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Rol del usuario (flujo ITIL por rol)
  const { user } = useAuth();
  const rol = user?.rol ?? '';
  const isCoordinador = rol === 'coordinador' || rol === 'administrador';
  const isTecnico = rol === 'tecnico';

  // Estado del ciclo de vida
  const estado = incidencia?.estado ?? '';
  const isCerrada = estado === 'finalizado' || estado === 'cancelado';
  const hasMantenimiento = !!incidencia?.mantenimiento_correctivo;

  // Acciones disponibles por rol y estado (ITIL — estado avanza por acción):
  //  - Coordinador ASIGNA (pendiente) -> en_ejecucion; y puede RE-ASIGNAR en
  //    en_ejecucion (cambiar de técnico) sin cambiar el estado.
  //  - Técnico completa MANTENIMIENTO (en_ejecucion) -> resuelto
  //  - Coordinador VERIFICA Y CIERRA (resuelto) -> finalizado (+ calibración)
  const canAsignar =
    isCoordinador && (estado === 'pendiente' || estado === 'en_ejecucion');
  const yaAsignada = estado === 'en_ejecucion';
  const canRegistrarMantenimiento =
    isTecnico && !hasMantenimiento && (estado === 'en_ejecucion' || estado === 'pendiente');
  const canCerrar = isCoordinador && estado === 'resuelto';
  const canCancelar = isCoordinador && !isCerrada;

  // Coordinador: asignar responsable (auto -> en_ejecucion en el backend)
  async function handleAsignar() {
    if (!incidencia) return;
    if (!editResponsable) {
      setSaveMsg({ text: 'Selecciona un responsable', isError: true });
      return;
    }
    setSaving(true);
    setSaveMsg(null);
    try {
      const reasignando = yaAsignada;
      await updateIncidencia(id, { responsable_id: Number(editResponsable) });
      await refreshIncidencia();
      setSaveMsg({
        text: reasignando ? 'Incidencia re-asignada' : 'Incidencia asignada al técnico',
        isError: false,
      });
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg({ text: err instanceof Error ? err.message : 'Error al asignar', isError: true });
    } finally {
      setSaving(false);
    }
  }

  // Coordinador: verificar y cerrar (finalizado -> dispara calibración)
  async function handleCerrar() {
    setSaving(true);
    setSaveMsg(null);
    try {
      await updateIncidencia(id, { estado: 'finalizado' });
      await refreshIncidencia();
      setSaveMsg({ text: 'Incidencia cerrada — se generó la calibración', isError: false });
      setTimeout(() => setSaveMsg(null), 4000);
    } catch (err) {
      setSaveMsg({ text: err instanceof Error ? err.message : 'Error al cerrar', isError: true });
    } finally {
      setSaving(false);
    }
  }

  async function handleCancelar() {
    if (!confirm('¿Cancelar esta incidencia? (falso positivo / no aplica)')) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      await updateIncidencia(id, { estado: 'cancelado' });
      await refreshIncidencia();
      setSaveMsg({ text: 'Incidencia cancelada', isError: false });
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg({ text: err instanceof Error ? err.message : 'Error al cancelar', isError: true });
    } finally {
      setSaving(false);
    }
  }

  // Técnico: registrar mantenimiento (auto -> resuelto en el backend)
  async function handleSubmitMantenimiento() {
    if (!mtoDiagnostico.trim() || !mtoAcciones.trim() || !mtoConclusion.trim()) {
      setSaveMsg({ text: 'Diagnóstico, Acciones y Conclusión son obligatorios', isError: true });
      return;
    }
    setSaving(true);
    setSaveMsg(null);
    try {
      await submitMantenimiento(id, {
        diagnostico: mtoDiagnostico,
        acciones_realizadas: mtoAcciones,
        conclusion: mtoConclusion,
        fecha_ejecucion: new Date().toISOString(),
        repuesto_ids: selectedRepuestoIds,
        adjuntos: adjuntos.filter((a) => a.filename && a.file_url),
      });
      await refreshIncidencia();
      setSaveMsg({ text: 'Mantenimiento registrado — incidencia marcada como Resuelta', isError: false });
      setTimeout(() => setSaveMsg(null), 4000);
    } catch (err) {
      setSaveMsg({ text: err instanceof Error ? err.message : 'Error al guardar', isError: true });
    } finally {
      setSaving(false);
    }
  }

  async function refreshIncidencia() {
    const refreshed = await fetchIncidencia(id);
    setIncidencia(refreshed);
    setEditResponsable(refreshed.responsable_id ? String(refreshed.responsable_id) : '');
    if (refreshed.mantenimiento_correctivo) {
      setMtoDiagnostico(refreshed.mantenimiento_correctivo.diagnostico ?? '');
      setMtoAcciones(refreshed.mantenimiento_correctivo.acciones_realizadas ?? '');
      setMtoConclusion(refreshed.mantenimiento_correctivo.conclusion ?? '');
    }
  }

  async function handleLinkProblema(problemaId: number | null) {
    try {
      const updated = await linkIncidenciaProblema(id, problemaId);
      setIncidencia(updated);
      setSaveMsg({ text: problemaId ? 'Vinculada al problema' : 'Desvinculada', isError: false });
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg({ text: err instanceof Error ? err.message : 'Error al vincular', isError: true });
    }
  }

  function toggleRepuesto(repId: number) {
    setSelectedRepuestoIds((prev) =>
      prev.includes(repId) ? prev.filter((r) => r !== repId) : [...prev, repId],
    );
  }

  function addAdjunto() {
    setAdjuntos((prev) => [...prev, { filename: '', file_url: '' }]);
  }

  function updateAdjunto(index: number, field: 'filename' | 'file_url', value: string) {
    setAdjuntos((prev) => prev.map((a, i) => (i === index ? { ...a, [field]: value } : a)));
  }

  function removeAdjunto(index: number) {
    setAdjuntos((prev) => prev.filter((_, i) => i !== index));
  }

  // Group repuestos by category
  const repuestosByCategoria = repuestos.reduce<Record<string, Repuesto[]>>((acc, r) => {
    if (!acc[r.categoria]) acc[r.categoria] = [];
    acc[r.categoria].push(r);
    return acc;
  }, {});

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
  const mto = incidencia.mantenimiento_correctivo;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
            Incidencia #{incidencia.id}
          </h1>
          <StatusBadge status={incidencia.estado} />
        </div>
        <div className="flex gap-2">
          {/* Coordinador: verificar y cerrar (resuelto -> finalizado + calibración) */}
          {canCerrar && (
            <button
              onClick={handleCerrar}
              disabled={saving}
              className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              Verificar y cerrar
            </button>
          )}
          {/* Coordinador: cancelar (falso positivo) */}
          {canCancelar && (
            <button
              onClick={handleCancelar}
              disabled={saving}
              className="rounded-md border border-red-300 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50 dark:border-red-700 dark:text-red-400"
            >
              Cancelar
            </button>
          )}
          {incidencia.problema_id && (
            <Link
              href={`/problemas/${incidencia.problema_id}`}
              className="rounded-md border border-purple-300 px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-50 dark:border-purple-700 dark:text-purple-300"
            >
              Ver Problema #{incidencia.problema_id}
            </Link>
          )}
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
              <Badge label="Correctiva" variant="danger" />
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
            <dt className="text-xs font-medium uppercase text-zinc-500">Estado</dt>
            <dd className="mt-0.5">
              <StatusBadge status={incidencia.estado} />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">
              Responsable
            </dt>
            <dd className="mt-0.5">
              {/* Coordinador ASIGNA (pendiente) o RE-ASIGNA (en_ejecucion): selector
                  + botón. Solo técnicos ACTIVOS. */}
              {canAsignar ? (
                <div className="flex flex-col gap-1">
                  {yaAsignada && (
                    <span className="text-xs text-zinc-500 dark:text-zinc-400">
                      Asignada a:{' '}
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">
                        {responsable ? `${responsable.nombre} ${responsable.apellido}` : '—'}
                      </span>
                    </span>
                  )}
                  <div className="flex items-center gap-2">
                    <select
                      value={editResponsable}
                      onChange={(e) => setEditResponsable(e.target.value)}
                      className="rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                    >
                      <option value="" disabled>Seleccionar técnico</option>
                      {usuarios
                        .filter((u) => u.rol === 'tecnico' && u.estado === 'activo')
                        .map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.nombre} {u.apellido}
                          </option>
                        ))}
                    </select>
                    <button
                      onClick={handleAsignar}
                      disabled={saving || !editResponsable}
                      className="rounded-md bg-blue-600 px-2.5 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {yaAsignada ? 'Re-asignar' : 'Asignar'}
                    </button>
                  </div>
                </div>
              ) : (
                <span className="text-sm text-zinc-900 dark:text-zinc-100">
                  {responsable ? `${responsable.nombre} ${responsable.apellido}` : 'Sin asignar'}
                </span>
              )}
            </dd>
          </div>
          {/* ITIL: impacto × urgencia = prioridad (derivada) + categoría */}
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Impacto</dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {(incidencia.impacto ?? 'media').replace(/^\w/, (c) => c.toUpperCase())}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Urgencia</dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {(incidencia.urgencia ?? 'media').replace(/^\w/, (c) => c.toUpperCase())}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Categoría</dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {(incidencia.categoria ?? 'otro').replace(/^\w/, (c) => c.toUpperCase())}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Creada</dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {new Date(incidencia.created_at).toLocaleString()}
            </dd>
          </div>
        </div>

        {/* ITIL: timeline SLA */}
        <div className="mb-4 grid grid-cols-3 gap-4 rounded-md bg-zinc-50 p-3 dark:bg-zinc-800/50">
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Asignación</dt>
            <dd className="mt-0.5 text-xs text-zinc-700 dark:text-zinc-300">
              {fmtDate(incidencia.fecha_asignacion)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Resolución</dt>
            <dd className="mt-0.5 text-xs text-zinc-700 dark:text-zinc-300">
              {fmtDate(incidencia.fecha_resolucion)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-zinc-500">Cierre</dt>
            <dd className="mt-0.5 text-xs text-zinc-700 dark:text-zinc-300">
              {fmtDate(incidencia.fecha_cierre)}
            </dd>
          </div>
        </div>

        {incidencia.descripcion && (
          <div className="mb-4">
            <dt className="text-xs font-medium uppercase text-zinc-500">Descripcion</dt>
            <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
              {incidencia.descripcion}
            </dd>
          </div>
        )}

        {/* ITIL: vincular a un Problema (causa raíz) — gestión del coordinador */}
        {isCoordinador && !isCerrada && (
          <div className="border-t border-zinc-200 pt-4 dark:border-zinc-700">
            <dt className="text-xs font-medium uppercase text-zinc-500">
              Problema (causa raíz)
            </dt>
            <dd className="mt-1">
              <select
                value={incidencia.problema_id ?? ''}
                onChange={(e) =>
                  handleLinkProblema(e.target.value ? Number(e.target.value) : null)
                }
                className="rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              >
                <option value="">Sin problema vinculado</option>
                {problemas.map((p) => (
                  <option key={p.id} value={p.id}>
                    #{p.id} — {p.titulo}
                  </option>
                ))}
              </select>
            </dd>
          </div>
        )}
      </div>

      {/* Mantenimiento Correctivo */}
      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        <h2 className="mb-4 text-lg font-bold text-zinc-900 dark:text-white">
          Mantenimiento Correctivo
        </h2>

        {/* Vista solo-lectura, salvo que el técnico deba registrar el mantenimiento */}
        {(!canRegistrarMantenimiento || hasMantenimiento) ? (
          <div className="space-y-4">
            {mto ? (
              <>
                <div>
                  <dt className="text-xs font-medium uppercase text-zinc-500">Diagnostico</dt>
                  <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">
                    {mto.diagnostico || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase text-zinc-500">Acciones Realizadas</dt>
                  <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">
                    {mto.acciones_realizadas || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase text-zinc-500">Conclusion</dt>
                  <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">
                    {mto.conclusion || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase text-zinc-500">Fecha de Ejecucion</dt>
                  <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                    {mto.fecha_ejecucion
                      ? new Date(mto.fecha_ejecucion).toLocaleDateString()
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase text-zinc-500">Repuestos</dt>
                  <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                    {mto.repuestos && mto.repuestos.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-0.5">
                        {mto.repuestos.map((r) => (
                          <li key={r.id}>
                            {r.nombre}{' '}
                            <span className="text-xs text-zinc-400">({r.categoria})</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      '—'
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase text-zinc-500">Adjuntos (fotos)</dt>
                  <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                    {mto.adjuntos && mto.adjuntos.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-0.5">
                        {mto.adjuntos.map((a) => (
                          <li key={a.id}>
                            <a
                              href={a.file_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline dark:text-blue-400"
                            >
                              {a.filename}
                            </a>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      '—'
                    )}
                  </dd>
                </div>
              </>
            ) : (
              <p className="text-sm text-zinc-400">
                No se ha registrado mantenimiento correctivo aun.
              </p>
            )}
          </div>
        ) : (
          /* Edit mode WITHOUT existing mantenimiento */
          <div className="space-y-4">
            {/* Diagnostico */}
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Diagnostico <span className="text-red-500">*</span>
              </label>
              <textarea
                value={mtoDiagnostico}
                onChange={(e) => setMtoDiagnostico(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              />
            </div>

            {/* Acciones Realizadas */}
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Acciones Realizadas <span className="text-red-500">*</span>
              </label>
              <textarea
                value={mtoAcciones}
                onChange={(e) => setMtoAcciones(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              />
            </div>

            {/* Conclusion */}
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Conclusion <span className="text-red-500">*</span>
              </label>
              <textarea
                value={mtoConclusion}
                onChange={(e) => setMtoConclusion(e.target.value)}
                rows={2}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              />
            </div>

            {/* Fecha de Ejecucion (readonly) */}
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Fecha de Ejecucion
              </label>
              <input
                type="date"
                value={new Date().toISOString().split('T')[0]}
                readOnly
                className="w-full rounded-md border border-zinc-300 bg-zinc-100 px-3 py-2 text-sm cursor-not-allowed dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
              />
            </div>

            {/* Repuestos multi-select */}
            <div ref={repuestosRef} className="relative">
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Repuestos
              </label>
              <button
                type="button"
                onClick={() => setRepuestosOpen((prev) => !prev)}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-left text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              >
                {selectedRepuestoIds.length === 0
                  ? 'Seleccionar repuestos...'
                  : `${selectedRepuestoIds.length} repuesto${selectedRepuestoIds.length > 1 ? 's' : ''} seleccionado${selectedRepuestoIds.length > 1 ? 's' : ''}`}
                <span className="float-right">{repuestosOpen ? '\u25B2' : '\u25BC'}</span>
              </button>

              {repuestosOpen && (
                <div className="absolute z-10 mt-1 max-h-60 w-full overflow-y-auto rounded-md border border-zinc-300 bg-white shadow-lg dark:border-zinc-600 dark:bg-zinc-800">
                  {Object.entries(repuestosByCategoria).map(([cat, items]) => (
                    <div key={cat}>
                      <div className="sticky top-0 bg-zinc-100 px-3 py-1.5 text-xs font-bold uppercase text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300">
                        {cat}
                      </div>
                      {items.map((r) => (
                        <label
                          key={r.id}
                          className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-700 dark:text-zinc-200"
                        >
                          <input
                            type="checkbox"
                            checked={selectedRepuestoIds.includes(r.id)}
                            onChange={() => toggleRepuesto(r.id)}
                            className="rounded border-zinc-300 dark:border-zinc-500"
                          />
                          {r.nombre}
                        </label>
                      ))}
                    </div>
                  ))}
                  {repuestos.length === 0 && (
                    <div className="px-3 py-2 text-sm text-zinc-400">No hay repuestos disponibles</div>
                  )}
                </div>
              )}
            </div>

            {/* Adjuntos */}
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Adjuntos (fotos)
              </label>
              <div className="space-y-2">
                {adjuntos.map((a, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Nombre del archivo"
                      value={a.filename}
                      onChange={(e) => updateAdjunto(i, 'filename', e.target.value)}
                      className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                    />
                    <input
                      type="text"
                      placeholder="URL del archivo"
                      value={a.file_url}
                      onChange={(e) => updateAdjunto(i, 'file_url', e.target.value)}
                      className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                    />
                    <button
                      type="button"
                      onClick={() => removeAdjunto(i)}
                      className="text-sm text-red-400 hover:text-red-300"
                    >
                      Eliminar
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={addAdjunto}
                className="mt-2 rounded-md border border-dashed border-zinc-400 px-3 py-1.5 text-sm text-zinc-600 hover:border-zinc-500 hover:text-zinc-700 dark:border-zinc-500 dark:text-zinc-400 dark:hover:border-zinc-400 dark:hover:text-zinc-300"
              >
                + Agregar Adjunto
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Técnico: guardar el mantenimiento correctivo (-> incidencia Resuelta) */}
      <div className="mt-6 flex items-center gap-3">
        {canRegistrarMantenimiento && !hasMantenimiento && (
          <button
            onClick={handleSubmitMantenimiento}
            disabled={saving}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Guardando...' : 'Guardar mantenimiento'}
          </button>
        )}
        {saveMsg && (
          <span className={`text-sm ${saveMsg.isError ? 'text-red-500' : 'text-green-600'}`}>
            {saveMsg.text}
          </span>
        )}
      </div>
    </div>
  );
}
