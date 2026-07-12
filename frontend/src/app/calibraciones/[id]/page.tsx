'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  fetchCalibracion,
  updateCalibracion,
  fetchProveedores,
} from '@/lib/api/ops';
import StatusBadge from '@/components/ui/StatusBadge';
import type { CalibracionOps, Proveedor } from '@/types/ops';

export default function CalibracionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = Number(params.id);
  const requestedMode = searchParams.get('mode');

  const [calibracion, setCalibracion] = useState<CalibracionOps | null>(null);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit form
  const [nota, setNota] = useState('');
  const [certificadoUrl, setCertificadoUrl] = useState('');
  const [proveedorId, setProveedorId] = useState('');
  const [fechaCalibracion, setFechaCalibracion] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{
    text: string;
    isError: boolean;
  } | null>(null);

  useEffect(() => {
    Promise.all([fetchCalibracion(id), fetchProveedores()])
      .then(([cal, provs]) => {
        setCalibracion(cal);
        setNota(cal.nota ?? '');
        setCertificadoUrl(cal.certificado_url ?? '');
        setProveedorId(cal.proveedor_id ? String(cal.proveedor_id) : '');
        setFechaCalibracion(
          cal.fecha_calibracion ? cal.fecha_calibracion.slice(0, 10) : '',
        );
        setProveedores(provs);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  // Determine mode
  const isFinalizado = calibracion?.estado === 'completada';
  const isEditMode = requestedMode === 'edit' && !isFinalizado;

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);

    // Validar campos obligatorios
    if (
      !fechaCalibracion ||
      !nota.trim() ||
      !certificadoUrl.trim() ||
      !proveedorId
    ) {
      setSaveMsg({
        text: 'Todos los campos son obligatorios: Fecha, Nota, URL Certificado y Proveedor',
        isError: true,
      });
      setSaving(false);
      return;
    }

    try {
      const updated = await updateCalibracion(id, {
        nota,
        certificado_url: certificadoUrl,
        proveedor_id: Number(proveedorId),
        fecha_calibracion: fechaCalibracion,
      });
      setCalibracion(updated);
      setSaveMsg({ text: 'Cambios guardados', isError: false });
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg({
        text: err instanceof Error ? err.message : 'Error al guardar',
        isError: true,
      });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center text-zinc-400">
        Cargando...
      </div>
    );
  }

  if (error || !calibracion) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error ?? 'Calibracion no encontrada'}
        </div>
      </div>
    );
  }

  const proveedor = proveedores.find((p) => p.id === calibracion.proveedor_id);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
            Calibracion #{calibracion.id}
          </h1>
          {isEditMode ? (
            <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
              Editando
            </span>
          ) : (
            <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300">
              Solo lectura
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {!isEditMode && !isFinalizado && (
            <Link
              href={`/calibraciones/${id}?mode=edit`}
              className="rounded-md bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600"
            >
              Editar
            </Link>
          )}
          {calibracion.incidencia_id && (
            <Link
              href={`/incidencias/${calibracion.incidencia_id}`}
              className="rounded-md border border-blue-300 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 dark:border-blue-600 dark:text-blue-400"
            >
              Ver Incidencia #{calibracion.incidencia_id}
            </Link>
          )}
          <button
            onClick={() => router.back()}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
          >
            Volver
          </button>
        </div>
      </div>

      {/* Info resumida */}
      <div className="mb-6 grid grid-cols-2 gap-4 rounded-lg border border-zinc-200 bg-white p-6 sm:grid-cols-3 dark:border-zinc-700 dark:bg-zinc-900">
        <div>
          <dt className="text-xs font-medium text-zinc-500 uppercase">
            Equipo
          </dt>
          <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
            {calibracion.device_id}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-zinc-500 uppercase">
            Estado
          </dt>
          <dd className="mt-0.5">
            <StatusBadge status={calibracion.estado} />
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-zinc-500 uppercase">
            Creada
          </dt>
          <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
            {new Date(calibracion.created_at).toLocaleString()}
          </dd>
        </div>
      </div>

      {/* Content: Read-only or Edit */}
      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        {isEditMode ? (
          <>
            <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-white">
              Editar Calibracion
            </h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Fecha Calibracion <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={fechaCalibracion}
                  onChange={(e) => setFechaCalibracion(e.target.value)}
                  required
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Nota <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={nota}
                  onChange={(e) => setNota(e.target.value)}
                  rows={3}
                  required
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  URL Certificado <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={certificadoUrl}
                  onChange={(e) => setCertificadoUrl(e.target.value)}
                  placeholder="https://..."
                  required
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Proveedor <span className="text-red-500">*</span>
                </label>
                <select
                  value={proveedorId}
                  onChange={(e) => setProveedorId(e.target.value)}
                  required
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                >
                  <option value="" disabled>
                    Seleccionar proveedor
                  </option>
                  {proveedores.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Guardando...' : 'Guardar'}
                </button>
                <Link
                  href={`/calibraciones/${id}`}
                  className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
                >
                  Cancelar
                </Link>
                {saveMsg && (
                  <span
                    className={`text-sm ${saveMsg.isError ? 'text-red-500' : 'text-green-600'}`}
                  >
                    {saveMsg.text}
                  </span>
                )}
              </div>
            </form>
          </>
        ) : (
          <>
            <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-white">
              Detalle de Calibracion
            </h2>
            <div className="space-y-4">
              <div>
                <dt className="text-xs font-medium text-zinc-500 uppercase">
                  Fecha Calibracion
                </dt>
                <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                  {calibracion.fecha_calibracion
                    ? new Date(
                        calibracion.fecha_calibracion,
                      ).toLocaleDateString()
                    : 'Pendiente'}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-zinc-500 uppercase">
                  Nota
                </dt>
                <dd className="mt-1 text-sm whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
                  {calibracion.nota || '—'}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-zinc-500 uppercase">
                  Certificado
                </dt>
                <dd className="mt-1 text-sm">
                  {calibracion.certificado_url ? (
                    <a
                      href={calibracion.certificado_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-blue-600 hover:underline"
                    >
                      {calibracion.certificado_url}
                    </a>
                  ) : (
                    <span className="text-zinc-400">—</span>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-zinc-500 uppercase">
                  Proveedor
                </dt>
                <dd className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                  {proveedor?.nombre ?? 'Sin proveedor'}
                </dd>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
