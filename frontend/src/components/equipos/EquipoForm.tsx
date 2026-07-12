'use client';

import { useState } from 'react';
import type { Equipo } from '@/types/lectura';

interface EquipoFormProps {
  initialData?: Partial<Equipo>;
  mode: 'create' | 'edit';
  onSubmit: (data: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}

export default function EquipoForm({
  initialData,
  mode,
  onSubmit,
  onCancel,
}: EquipoFormProps) {
  const [form, setForm] = useState({
    device_id: initialData?.device_id ?? '',
    nombre: initialData?.nombre ?? '',
    tipo: initialData?.tipo ?? '',
    ubicacion: initialData?.ubicacion ?? '',
    serie: initialData?.serie ?? '',
    marca: initialData?.marca ?? '',
    modelo: initialData?.modelo ?? '',
    parametro_medicion: initialData?.parametro_medicion ?? '',
    rango_medicion: initialData?.rango_medicion ?? '',
    criticidad: initialData?.criticidad ?? 'media',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(form)) {
        if (value !== '') data[key] = value;
      }
      await onSubmit(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  }

  const fields = [
    {
      name: 'device_id',
      label: 'Device ID',
      required: true,
      disabled: mode === 'edit',
    },
    { name: 'nombre', label: 'Nombre' },
    { name: 'tipo', label: 'Tipo' },
    { name: 'ubicacion', label: 'Ubicacion' },
    { name: 'serie', label: 'Serie' },
    { name: 'marca', label: 'Marca' },
    { name: 'modelo', label: 'Modelo' },
    { name: 'parametro_medicion', label: 'Parametro Medicion' },
    { name: 'rango_medicion', label: 'Rango Medicion' },
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {fields.map((field) => (
          <div key={field.name}>
            <label
              htmlFor={field.name}
              className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {field.label}
              {field.required && <span className="text-red-500"> *</span>}
            </label>
            <input
              id={field.name}
              name={field.name}
              type="text"
              value={form[field.name as keyof typeof form]}
              onChange={handleChange}
              required={field.required}
              disabled={field.disabled}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:bg-zinc-100 disabled:text-zinc-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-white dark:disabled:bg-zinc-900"
            />
          </div>
        ))}

        <div>
          <label
            htmlFor="criticidad"
            className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300"
          >
            Criticidad
          </label>
          <select
            id="criticidad"
            name="criticidad"
            value={form.criticidad}
            onChange={handleChange}
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          >
            <option value="alta">Alta</option>
            <option value="media">Media</option>
            <option value="baja">Baja</option>
          </select>
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting
            ? 'Guardando...'
            : mode === 'create'
              ? 'Crear Equipo'
              : 'Guardar Cambios'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
