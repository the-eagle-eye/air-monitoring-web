'use client';

import { useState, useEffect } from 'react';
import { fetchEquipos } from '@/lib/api/lecturas';
import { fetchUsuarios } from '@/lib/api/ops';
import type { Equipo } from '@/types/lectura';
import type { Usuario } from '@/types/ops';

interface IncidenciaFormProps {
  onSubmit: (data: {
    device_id: string;
    tipo: string;
    prioridad: string;
    descripcion?: string;
    responsable_id?: number;
  }) => Promise<void>;
  onCancel: () => void;
}

export default function IncidenciaForm({
  onSubmit,
  onCancel,
}: IncidenciaFormProps) {
  const [equipos, setEquipos] = useState<Equipo[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [form, setForm] = useState({
    device_id: '',
    tipo: 'correctiva',
    prioridad: 'media',
    descripcion: '',
    responsable_id: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEquipos()
      .then(setEquipos)
      .catch(() => {});
    fetchUsuarios()
      .then(setUsuarios)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (equipos.length > 0 && !form.device_id) {
      setForm((prev) => ({ ...prev, device_id: equipos[0].device_id }));
    }
  }, [equipos, form.device_id]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (!form.responsable_id) {
        setError('Responsable es obligatorio');
        setSubmitting(false);
        return;
      }
      await onSubmit({
        device_id: form.device_id,
        tipo: form.tipo,
        prioridad: form.prioridad,
        descripcion: form.descripcion || undefined,
        responsable_id: Number(form.responsable_id),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Equipo <span className="text-red-500">*</span>
          </label>
          <select
            value={form.device_id}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, device_id: e.target.value }))
            }
            required
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
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
            Tipo <span className="text-red-500">*</span>
          </label>
          <select
            value={form.tipo}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, tipo: e.target.value }))
            }
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          >
            <option value="correctiva">Correctiva</option>
            <option value="calibracion">Calibracion</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Prioridad
          </label>
          <select
            value={form.prioridad}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, prioridad: e.target.value }))
            }
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          >
            <option value="alta">Alta</option>
            <option value="media">Media</option>
            <option value="baja">Baja</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Responsable <span className="text-red-500">*</span>
          </label>
          <select
            value={form.responsable_id}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, responsable_id: e.target.value }))
            }
            required
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          >
            <option value="" disabled>
              Seleccionar responsable
            </option>
            {usuarios.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre} {u.apellido} ({u.rol})
              </option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-2">
          <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Descripcion
          </label>
          <textarea
            value={form.descripcion}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, descripcion: e.target.value }))
            }
            rows={3}
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          />
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? 'Creando...' : 'Crear Incidencia'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
