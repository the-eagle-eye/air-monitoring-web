'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  fetchCalibracion,
  updateCalibracion,
  fetchProveedores,
} from '@/lib/api/ops';
import type { CalibracionOps, Proveedor } from '@/types/ops';

export default function CalibracionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

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
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchCalibracion(id), fetchProveedores()])
      .then(([cal, provs]) => {
        setCalibracion(cal);
        setNota(cal.nota ?? '');
        setCertificadoUrl(cal.certificado_url ?? '');
        setProveedorId(cal.proveedor_id ? String(cal.proveedor_id) : '');
        setFechaCalibracion(
          cal.fecha_calibracion
            ? cal.fecha_calibracion.slice(0, 16)
            : '',
        );
        setProveedores(provs);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    try {
      const updated = await updateCalibracion(id, {
        nota: nota || undefined,
        certificado_url: certificadoUrl || undefined,
        proveedor_id: proveedorId ? Number(proveedorId) : undefined,
        fecha_calibracion: fechaCalibracion || undefined,
      });
      setCalibracion(updated);
      setSaveMsg('Cambios guardados');
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-3xl px-4 py-12 text-center text-zinc-400">Cargando...</div>;
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
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Calibracion #{calibracion.id}
        </h1>
        <div className="flex gap-2">
          <Link
            href={`/incidencias/${calibracion.incidencia_id}`}
            className="rounded-md border border-blue-300 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 dark:border-blue-600 dark:text-blue-400"
          >
            Ver Incidencia #{calibracion.incidencia_id}
          </Link>
          <button
            onClick={() => router.back()}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
          >
            Volver
          </button>
        </div>
      </div>

      {/* Info resumida */}
      <div className="mb-6 grid grid-cols-2 gap-4 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        <div>
          <dt className="text-xs font-medium uppercase text-zinc-500">Equipo</dt>
          <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
            {calibracion.device_id}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase text-zinc-500">Proveedor</dt>
          <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
            {proveedor?.nombre ?? 'Sin proveedor'}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase text-zinc-500">Creada</dt>
          <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
            {new Date(calibracion.created_at).toLocaleString()}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase text-zinc-500">Incidencia</dt>
          <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
            #{calibracion.incidencia_id}
          </dd>
        </div>
      </div>

      {/* Formulario edicion */}
      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-white">
          Editar Calibracion
        </h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Fecha Calibracion
            </label>
            <input
              type="datetime-local"
              value={fechaCalibracion}
              onChange={(e) => setFechaCalibracion(e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Nota
            </label>
            <textarea
              value={nota}
              onChange={(e) => setNota(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              URL Certificado
            </label>
            <input
              type="text"
              value={certificadoUrl}
              onChange={(e) => setCertificadoUrl(e.target.value)}
              placeholder="https://..."
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Proveedor
            </label>
            <select
              value={proveedorId}
              onChange={(e) => setProveedorId(e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            >
              <option value="">Sin proveedor</option>
              {proveedores.map((p) => (
                <option key={p.id} value={p.id}>{p.nombre}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Guardando...' : 'Guardar Cambios'}
            </button>
            {saveMsg && (
              <span className="text-sm text-green-600">{saveMsg}</span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
