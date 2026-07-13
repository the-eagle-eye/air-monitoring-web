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
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Pre-selecciona el responsable en el selector SOLO si es un técnico activo
// (los que aparecen en la lista); si no, deja el placeholder para forzar elección.
function safeEditResponsable(
  inc: { responsable_id: number | null },
  users: Usuario[],
): string {
  const esTecnicoActivo = users.some(
    (u) =>
      u.id === inc.responsable_id &&
      u.rol === 'tecnico' &&
      u.estado === 'activo',
  );
  return esTecnicoActivo && inc.responsable_id
    ? String(inc.responsable_id)
    : '';
}

function prioridadVariant(p: string): 'danger' | 'warning' | 'success' {
  if (p === 'alta') return 'danger';
  if (p === 'media') return 'warning';
  return 'success';
}

function capitalize(s: string | null | undefined, fallback = 'otro'): string {
  return (s ?? fallback).replace(/^\w/, (c) => c.toUpperCase());
}

type HeaderActionsProps = {
  incidencia: Incidencia;
  canCerrar: boolean;
  canCancelar: boolean;
  saving: boolean;
  onCerrar: () => void;
  onCancelar: () => void;
  onBack: () => void;
};

function HeaderActions({
  incidencia,
  canCerrar,
  canCancelar,
  saving,
  onCerrar,
  onCancelar,
  onBack,
}: HeaderActionsProps) {
  return (
    <div className="flex gap-2">
      {canCerrar && (
        <button
          onClick={onCerrar}
          disabled={saving}
          className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          Verificar y cerrar
        </button>
      )}
      {canCancelar && (
        <button
          onClick={onCancelar}
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
        onClick={onBack}
        className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
      >
        Volver
      </button>
    </div>
  );
}

type AsignarInlineProps = {
  usuarios: Usuario[];
  responsable: Usuario | undefined;
  editResponsable: string;
  yaAsignada: boolean;
  saving: boolean;
  onEditResponsable: (v: string) => void;
  onAsignar: () => void;
};

function AsignarResponsableInline({
  usuarios,
  responsable,
  editResponsable,
  yaAsignada,
  saving,
  onEditResponsable,
  onAsignar,
}: AsignarInlineProps) {
  const tecnicos = usuarios.filter(
    (u) => u.rol === 'tecnico' && u.estado === 'activo',
  );
  return (
    <div className="flex flex-col gap-1">
      {yaAsignada && (
        <span className="text-xs text-zinc-500 dark:text-zinc-400">
          Asignada a:{' '}
          <span className="font-medium text-zinc-700 dark:text-zinc-300">
            {responsable
              ? `${responsable.nombre} ${responsable.apellido}`
              : '—'}
          </span>
        </span>
      )}
      <div className="flex items-center gap-2">
        <select
          value={editResponsable}
          onChange={(e) => onEditResponsable(e.target.value)}
          className="rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        >
          <option value="" disabled>
            Seleccionar técnico
          </option>
          {tecnicos.map((u) => (
            <option key={u.id} value={u.id}>
              {u.nombre} {u.apellido}
            </option>
          ))}
        </select>
        <button
          onClick={onAsignar}
          disabled={saving || !editResponsable}
          className="rounded-md bg-blue-600 px-2.5 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {yaAsignada ? 'Re-asignar' : 'Asignar'}
        </button>
      </div>
    </div>
  );
}

type MantenimientoData = NonNullable<Incidencia['mantenimiento_correctivo']>;

function MantenimientoView({
  mto,
}: {
  mto: MantenimientoData | null | undefined;
}) {
  if (!mto) {
    return (
      <p className="text-sm text-zinc-400">
        No se ha registrado mantenimiento correctivo aun.
      </p>
    );
  }

  const fechaEjecucion = mto.fecha_ejecucion
    ? new Date(mto.fecha_ejecucion).toLocaleDateString()
    : '—';

  return (
    <div className="space-y-4">
      <div>
        <dt className="text-xs font-medium text-zinc-500 uppercase">
          Diagnostico
        </dt>
        <dd className="mt-1 text-sm whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
          {mto.diagnostico || '—'}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-medium text-zinc-500 uppercase">
          Acciones Realizadas
        </dt>
        <dd className="mt-1 text-sm whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
          {mto.acciones_realizadas || '—'}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-medium text-zinc-500 uppercase">
          Conclusion
        </dt>
        <dd className="mt-1 text-sm whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
          {mto.conclusion || '—'}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-medium text-zinc-500 uppercase">
          Fecha de Ejecucion
        </dt>
        <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
          {fechaEjecucion}
        </dd>
      </div>
      <MantenimientoRepuestos repuestos={mto.repuestos} />
      <MantenimientoAdjuntos adjuntos={mto.adjuntos} />
    </div>
  );
}

function MantenimientoRepuestos({
  repuestos,
}: {
  repuestos: MantenimientoData['repuestos'];
}) {
  const hasItems = repuestos && repuestos.length > 0;
  return (
    <div>
      <dt className="text-xs font-medium text-zinc-500 uppercase">Repuestos</dt>
      <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
        {hasItems ? (
          <ul className="list-disc space-y-0.5 pl-5">
            {repuestos!.map((r) => (
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
  );
}

function MantenimientoAdjuntos({
  adjuntos,
}: {
  adjuntos: MantenimientoData['adjuntos'];
}) {
  const hasItems = adjuntos && adjuntos.length > 0;
  return (
    <div>
      <dt className="text-xs font-medium text-zinc-500 uppercase">
        Adjuntos (fotos)
      </dt>
      <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
        {hasItems ? (
          <ul className="list-disc space-y-0.5 pl-5">
            {adjuntos!.map((a) => (
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
  );
}

type RepuestosMultiSelectProps = {
  repuestos: Repuesto[];
  selectedRepuestoIds: number[];
  open: boolean;
  setOpen: (fn: (prev: boolean) => boolean) => void;
  toggleRepuesto: (id: number) => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
};

function RepuestosMultiSelect({
  repuestos,
  selectedRepuestoIds,
  open,
  setOpen,
  toggleRepuesto,
  containerRef,
}: RepuestosMultiSelectProps) {
  const repuestosByCategoria = repuestos.reduce<Record<string, Repuesto[]>>(
    (acc, r) => {
      if (!acc[r.categoria]) acc[r.categoria] = [];
      acc[r.categoria].push(r);
      return acc;
    },
    {},
  );
  const count = selectedRepuestoIds.length;
  const label =
    count === 0
      ? 'Seleccionar repuestos...'
      : `${count} repuesto${count > 1 ? 's' : ''} seleccionado${count > 1 ? 's' : ''}`;

  return (
    <div ref={containerRef} className="relative">
      <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
        Repuestos
      </label>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-left text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
      >
        {label}
        <span className="float-right">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="absolute z-10 mt-1 max-h-60 w-full overflow-y-auto rounded-md border border-zinc-300 bg-white shadow-lg dark:border-zinc-600 dark:bg-zinc-800">
          {Object.entries(repuestosByCategoria).map(([cat, items]) => (
            <div key={cat}>
              <div className="sticky top-0 bg-zinc-100 px-3 py-1.5 text-xs font-bold text-zinc-600 uppercase dark:bg-zinc-700 dark:text-zinc-300">
                {cat}
              </div>
              {items.map((r) => (
                <label
                  key={r.id}
                  className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:text-zinc-200 dark:hover:bg-zinc-700"
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
            <div className="px-3 py-2 text-sm text-zinc-400">
              No hay repuestos disponibles
            </div>
          )}
        </div>
      )}
    </div>
  );
}

type Adjunto = { filename: string; file_url: string };

type AdjuntosEditorProps = {
  adjuntos: Adjunto[];
  onAdd: () => void;
  onUpdate: (
    index: number,
    field: 'filename' | 'file_url',
    value: string,
  ) => void;
  onRemove: (index: number) => void;
};

function AdjuntosEditor({
  adjuntos,
  onAdd,
  onUpdate,
  onRemove,
}: AdjuntosEditorProps) {
  return (
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
              onChange={(e) => onUpdate(i, 'filename', e.target.value)}
              className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            />
            <input
              type="text"
              placeholder="URL del archivo"
              value={a.file_url}
              onChange={(e) => onUpdate(i, 'file_url', e.target.value)}
              className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            />
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="text-sm text-red-400 hover:text-red-300"
            >
              Eliminar
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={onAdd}
        className="mt-2 rounded-md border border-dashed border-zinc-400 px-3 py-1.5 text-sm text-zinc-600 hover:border-zinc-500 hover:text-zinc-700 dark:border-zinc-500 dark:text-zinc-400 dark:hover:border-zinc-400 dark:hover:text-zinc-300"
      >
        + Agregar Adjunto
      </button>
    </div>
  );
}

type MantenimientoFormProps = {
  mtoDiagnostico: string;
  mtoAcciones: string;
  mtoConclusion: string;
  onDiagnostico: (v: string) => void;
  onAcciones: (v: string) => void;
  onConclusion: (v: string) => void;
  repuestos: Repuesto[];
  selectedRepuestoIds: number[];
  repuestosOpen: boolean;
  setRepuestosOpen: (fn: (prev: boolean) => boolean) => void;
  toggleRepuesto: (id: number) => void;
  repuestosRef: React.RefObject<HTMLDivElement | null>;
  adjuntos: Adjunto[];
  addAdjunto: () => void;
  updateAdjunto: (
    index: number,
    field: 'filename' | 'file_url',
    value: string,
  ) => void;
  removeAdjunto: (index: number) => void;
};

function MantenimientoForm(props: MantenimientoFormProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Diagnostico <span className="text-red-500">*</span>
        </label>
        <textarea
          value={props.mtoDiagnostico}
          onChange={(e) => props.onDiagnostico(e.target.value)}
          rows={3}
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Acciones Realizadas <span className="text-red-500">*</span>
        </label>
        <textarea
          value={props.mtoAcciones}
          onChange={(e) => props.onAcciones(e.target.value)}
          rows={3}
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Conclusion <span className="text-red-500">*</span>
        </label>
        <textarea
          value={props.mtoConclusion}
          onChange={(e) => props.onConclusion(e.target.value)}
          rows={2}
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Fecha de Ejecucion
        </label>
        <input
          type="date"
          value={new Date().toISOString().split('T')[0]}
          readOnly
          className="w-full cursor-not-allowed rounded-md border border-zinc-300 bg-zinc-100 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
        />
      </div>

      <RepuestosMultiSelect
        repuestos={props.repuestos}
        selectedRepuestoIds={props.selectedRepuestoIds}
        open={props.repuestosOpen}
        setOpen={props.setRepuestosOpen}
        toggleRepuesto={props.toggleRepuesto}
        containerRef={props.repuestosRef}
      />

      <AdjuntosEditor
        adjuntos={props.adjuntos}
        onAdd={props.addAdjunto}
        onUpdate={props.updateAdjunto}
        onRemove={props.removeAdjunto}
      />
    </div>
  );
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

  const [editResponsable, setEditResponsable] = useState('');

  const [mtoDiagnostico, setMtoDiagnostico] = useState('');
  const [mtoAcciones, setMtoAcciones] = useState('');
  const [mtoConclusion, setMtoConclusion] = useState('');
  const [selectedRepuestoIds, setSelectedRepuestoIds] = useState<number[]>([]);
  const [repuestosOpen, setRepuestosOpen] = useState(false);
  const [adjuntos, setAdjuntos] = useState<Adjunto[]>([]);

  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{
    text: string;
    isError: boolean;
  } | null>(null);

  const repuestosRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([fetchIncidencia(id), fetchUsuarios(), fetchRepuestos()])
      .then(([inc, users, reps]) => {
        setIncidencia(inc);
        setEditResponsable(safeEditResponsable(inc, users));
        setUsuarios(users);
        setRepuestos(reps);
        fetchProblemas()
          .then((r) => setProblemas(r.items))
          .catch(() => {});
        if (inc.mantenimiento_correctivo) {
          setMtoDiagnostico(inc.mantenimiento_correctivo.diagnostico ?? '');
          setMtoAcciones(
            inc.mantenimiento_correctivo.acciones_realizadas ?? '',
          );
          setMtoConclusion(inc.mantenimiento_correctivo.conclusion ?? '');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        repuestosRef.current &&
        !repuestosRef.current.contains(e.target as Node)
      ) {
        setRepuestosOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const { user } = useAuth();
  const rol = user?.rol ?? '';
  const isCoordinador = rol === 'coordinador' || rol === 'administrador';
  const isTecnico = rol === 'tecnico';

  const estado = incidencia?.estado ?? '';
  const isCerrada = estado === 'finalizado' || estado === 'cancelado';
  const hasMantenimiento = !!incidencia?.mantenimiento_correctivo;

  const canAsignar =
    isCoordinador && (estado === 'pendiente' || estado === 'en_ejecucion');
  const yaAsignada = estado === 'en_ejecucion';
  const canRegistrarMantenimiento =
    isTecnico &&
    !hasMantenimiento &&
    (estado === 'en_ejecucion' || estado === 'pendiente');
  const canCerrar = isCoordinador && estado === 'resuelto';
  const canCancelar = isCoordinador && !isCerrada;

  async function refreshIncidencia() {
    const refreshed = await fetchIncidencia(id);
    setIncidencia(refreshed);
    setEditResponsable(safeEditResponsable(refreshed, usuarios));
    if (refreshed.mantenimiento_correctivo) {
      setMtoDiagnostico(refreshed.mantenimiento_correctivo.diagnostico ?? '');
      setMtoAcciones(
        refreshed.mantenimiento_correctivo.acciones_realizadas ?? '',
      );
      setMtoConclusion(refreshed.mantenimiento_correctivo.conclusion ?? '');
    }
  }

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
        text: reasignando
          ? 'Incidencia re-asignada'
          : 'Incidencia asignada al técnico',
        isError: false,
      });
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg({
        text: err instanceof Error ? err.message : 'Error al asignar',
        isError: true,
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleCerrar() {
    setSaving(true);
    setSaveMsg(null);
    try {
      await updateIncidencia(id, { estado: 'finalizado' });
      await refreshIncidencia();
      setSaveMsg({
        text: 'Incidencia cerrada — se generó la calibración',
        isError: false,
      });
      setTimeout(() => setSaveMsg(null), 4000);
    } catch (err) {
      setSaveMsg({
        text: err instanceof Error ? err.message : 'Error al cerrar',
        isError: true,
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleCancelar() {
    if (!confirm('¿Cancelar esta incidencia? (falso positivo / no aplica)'))
      return;
    setSaving(true);
    setSaveMsg(null);
    try {
      await updateIncidencia(id, { estado: 'cancelado' });
      await refreshIncidencia();
      setSaveMsg({ text: 'Incidencia cancelada', isError: false });
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg({
        text: err instanceof Error ? err.message : 'Error al cancelar',
        isError: true,
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmitMantenimiento() {
    if (
      !mtoDiagnostico.trim() ||
      !mtoAcciones.trim() ||
      !mtoConclusion.trim()
    ) {
      setSaveMsg({
        text: 'Diagnóstico, Acciones y Conclusión son obligatorios',
        isError: true,
      });
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
      setSaveMsg({
        text: 'Mantenimiento registrado — incidencia marcada como Resuelta',
        isError: false,
      });
      setTimeout(() => setSaveMsg(null), 4000);
    } catch (err) {
      setSaveMsg({
        text: err instanceof Error ? err.message : 'Error al guardar',
        isError: true,
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleLinkProblema(problemaId: number | null) {
    try {
      const updated = await linkIncidenciaProblema(id, problemaId);
      setIncidencia(updated);
      setSaveMsg({
        text: problemaId ? 'Vinculada al problema' : 'Desvinculada',
        isError: false,
      });
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg({
        text: err instanceof Error ? err.message : 'Error al vincular',
        isError: true,
      });
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

  function updateAdjunto(
    index: number,
    field: 'filename' | 'file_url',
    value: string,
  ) {
    setAdjuntos((prev) =>
      prev.map((a, i) => (i === index ? { ...a, [field]: value } : a)),
    );
  }

  function removeAdjunto(index: number) {
    setAdjuntos((prev) => prev.filter((_, i) => i !== index));
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12 text-center text-zinc-400">
        Cargando...
      </div>
    );
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
  const showMantenimientoView = !canRegistrarMantenimiento || hasMantenimiento;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
            Incidencia #{incidencia.id}
          </h1>
          <StatusBadge status={incidencia.estado} />
        </div>
        <HeaderActions
          incidencia={incidencia}
          canCerrar={canCerrar}
          canCancelar={canCancelar}
          saving={saving}
          onCerrar={handleCerrar}
          onCancelar={handleCancelar}
          onBack={() => router.back()}
        />
      </div>

      <div className="mb-8 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Equipo
            </dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {incidencia.device_id}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Tipo
            </dt>
            <dd className="mt-0.5">
              <Badge label="Correctiva" variant="danger" />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Prioridad
            </dt>
            <dd className="mt-0.5">
              <Badge
                label={capitalize(incidencia.prioridad)}
                variant={prioridadVariant(incidencia.prioridad)}
              />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Estado
            </dt>
            <dd className="mt-0.5">
              <StatusBadge status={incidencia.estado} />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Responsable
            </dt>
            <dd className="mt-0.5">
              {canAsignar ? (
                <AsignarResponsableInline
                  usuarios={usuarios}
                  responsable={responsable}
                  editResponsable={editResponsable}
                  yaAsignada={yaAsignada}
                  saving={saving}
                  onEditResponsable={setEditResponsable}
                  onAsignar={handleAsignar}
                />
              ) : (
                <span className="text-sm text-zinc-900 dark:text-zinc-100">
                  {responsable
                    ? `${responsable.nombre} ${responsable.apellido}`
                    : 'Sin asignar'}
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Impacto
            </dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {capitalize(incidencia.impacto, 'media')}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Urgencia
            </dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {capitalize(incidencia.urgencia, 'media')}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Categoría
            </dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {capitalize(incidencia.categoria, 'otro')}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Creada
            </dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {new Date(incidencia.created_at).toLocaleString()}
            </dd>
          </div>
        </div>

        <div className="mb-4 grid grid-cols-3 gap-4 rounded-md bg-zinc-50 p-3 dark:bg-zinc-800/50">
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Asignación
            </dt>
            <dd className="mt-0.5 text-xs text-zinc-700 dark:text-zinc-300">
              {fmtDate(incidencia.fecha_asignacion)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Resolución
            </dt>
            <dd className="mt-0.5 text-xs text-zinc-700 dark:text-zinc-300">
              {fmtDate(incidencia.fecha_resolucion)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Cierre
            </dt>
            <dd className="mt-0.5 text-xs text-zinc-700 dark:text-zinc-300">
              {fmtDate(incidencia.fecha_cierre)}
            </dd>
          </div>
        </div>

        {incidencia.descripcion && (
          <div className="mb-4">
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Descripcion
            </dt>
            <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
              {incidencia.descripcion}
            </dd>
          </div>
        )}

        {isCoordinador && !isCerrada && (
          <div className="border-t border-zinc-200 pt-4 dark:border-zinc-700">
            <dt className="text-xs font-medium text-zinc-500 uppercase">
              Problema (causa raíz)
            </dt>
            <dd className="mt-1">
              <select
                value={incidencia.problema_id ?? ''}
                onChange={(e) =>
                  handleLinkProblema(
                    e.target.value ? Number(e.target.value) : null,
                  )
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

      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        <h2 className="mb-4 text-lg font-bold text-zinc-900 dark:text-white">
          Mantenimiento Correctivo
        </h2>

        {showMantenimientoView ? (
          <MantenimientoView mto={mto} />
        ) : (
          <MantenimientoForm
            mtoDiagnostico={mtoDiagnostico}
            mtoAcciones={mtoAcciones}
            mtoConclusion={mtoConclusion}
            onDiagnostico={setMtoDiagnostico}
            onAcciones={setMtoAcciones}
            onConclusion={setMtoConclusion}
            repuestos={repuestos}
            selectedRepuestoIds={selectedRepuestoIds}
            repuestosOpen={repuestosOpen}
            setRepuestosOpen={setRepuestosOpen}
            toggleRepuesto={toggleRepuesto}
            repuestosRef={repuestosRef}
            adjuntos={adjuntos}
            addAdjunto={addAdjunto}
            updateAdjunto={updateAdjunto}
            removeAdjunto={removeAdjunto}
          />
        )}
      </div>

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
          <span
            className={`text-sm ${saveMsg.isError ? 'text-red-500' : 'text-green-600'}`}
          >
            {saveMsg.text}
          </span>
        )}
      </div>
    </div>
  );
}
