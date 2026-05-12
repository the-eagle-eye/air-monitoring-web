'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  fetchRepuestos,
  createRepuesto,
  updateRepuesto,
  deleteRepuesto,
} from '@/lib/api/ops';
import DataTable from '@/components/ui/DataTable';
import StatusBadge from '@/components/ui/StatusBadge';
import type { Repuesto } from '@/types/ops';

const CATEGORIAS = [
  'Sensores y Detectores',
  'Filtros y Consumibles',
  'Bombas y Sistemas de Muestreo',
  'Lamparas y Optica',
  'Componentes Electronicos',
  'Sistemas de Flujo y Gas',
  'Piezas Estructurales y Mecanicas',
  'Accesorios Generales',
];

export default function RepuestosPage() {
  const [repuestos, setRepuestos] = useState<Repuesto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterCategoria, setFilterCategoria] = useState('');

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formNombre, setFormNombre] = useState('');
  const [formCategoria, setFormCategoria] = useState(CATEGORIAS[0]);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(() => {
    setLoading(true);
    fetchRepuestos(filterCategoria || undefined)
      .then(setRepuestos)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filterCategoria]);

  useEffect(() => { loadData(); }, [loadData]);

  function openCreate() {
    setEditingId(null);
    setFormNombre('');
    setFormCategoria(CATEGORIAS[0]);
    setShowForm(true);
  }

  function openEdit(r: Repuesto) {
    setEditingId(r.id);
    setFormNombre(r.nombre);
    setFormCategoria(r.categoria);
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (editingId) {
        await updateRepuesto(editingId, { nombre: formNombre, categoria: formCategoria });
      } else {
        await createRepuesto({ nombre: formNombre, categoria: formCategoria });
      }
      setShowForm(false);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Desactivar este repuesto?')) return;
    try {
      await deleteRepuesto(id);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar');
    }
  }

  const columns = [
    { key: 'id', header: 'ID' },
    { key: 'nombre', header: 'Nombre' },
    { key: 'categoria', header: 'Categoria' },
    {
      key: 'estado',
      header: 'Estado',
      render: (item: Repuesto) => <StatusBadge status={item.estado} />,
    },
    {
      key: 'created_at',
      header: 'Creado',
      render: (item: Repuesto) => new Date(item.created_at).toLocaleDateString(),
    },
    {
      key: 'acciones',
      header: 'Acciones',
      render: (item: Repuesto) => (
        <div className="flex gap-2">
          <button
            onClick={() => openEdit(item)}
            className="rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400"
          >
            Editar
          </button>
          <button
            onClick={() => handleDelete(item.id)}
            className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-400"
          >
            Eliminar
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Repuestos
        </h1>
        <button
          onClick={() => showForm ? setShowForm(false) : openCreate()}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {showForm ? 'Cancelar' : 'Nuevo Repuesto'}
        </button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
          <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-white">
            {editingId ? 'Editar Repuesto' : 'Nuevo Repuesto'}
          </h2>
          <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-4">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Nombre
              </label>
              <input
                type="text"
                value={formNombre}
                onChange={(e) => setFormNombre(e.target.value)}
                required
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Categoria
              </label>
              <select
                value={formCategoria}
                onChange={(e) => setFormCategoria(e.target.value)}
                required
                className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              >
                {CATEGORIAS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Guardando...' : editingId ? 'Actualizar' : 'Crear'}
            </button>
          </form>
        </div>
      )}

      <div className="mb-4 flex items-center gap-3">
        <select
          value={filterCategoria}
          onChange={(e) => setFilterCategoria(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
        >
          <option value="">Todas las categorias</option>
          {CATEGORIAS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <span className="text-sm text-zinc-500">{repuestos.length} resultados</span>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="py-12 text-center text-zinc-400">Cargando...</div>
      ) : (
        <DataTable columns={columns} data={repuestos} keyExtractor={(r) => r.id} />
      )}
    </div>
  );
}
