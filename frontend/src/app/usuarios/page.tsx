'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  fetchUsuarios,
  createUsuario,
  updateUsuario,
  deleteUsuario,
} from '@/lib/api/ops';
import DataTable from '@/components/ui/DataTable';
import StatusBadge from '@/components/ui/StatusBadge';
import type { Usuario } from '@/types/ops';

const ROLES = ['administrador', 'tecnico', 'coordinador'];

const ROL_LABEL: Record<string, string> = {
  administrador: 'Admin',
  tecnico: 'Tecnico',
  coordinador: 'Coordinador',
};

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formEmail, setFormEmail] = useState('');
  const [formNombre, setFormNombre] = useState('');
  const [formApellido, setFormApellido] = useState('');
  const [formRol, setFormRol] = useState(ROLES[0]);
  const [formPassword, setFormPassword] = useState('');
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(() => {
    setLoading(true);
    fetchUsuarios()
      .then(setUsuarios)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function openCreate() {
    setEditingId(null);
    setFormEmail('');
    setFormNombre('');
    setFormApellido('');
    setFormRol(ROLES[0]);
    setFormPassword('');
    setShowForm(true);
  }

  function openEdit(u: Usuario) {
    setEditingId(u.id);
    setFormEmail(u.email);
    setFormNombre(u.nombre);
    setFormApellido(u.apellido);
    setFormRol(u.rol);
    setFormPassword('');
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (editingId) {
        const data: Record<string, string> = {
          nombre: formNombre,
          apellido: formApellido,
          rol: formRol,
        };
        if (formPassword) data.password = formPassword;
        await updateUsuario(editingId, data);
      } else {
        await createUsuario({
          email: formEmail,
          nombre: formNombre,
          apellido: formApellido,
          rol: formRol,
          password: formPassword,
        });
      }
      setShowForm(false);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(id: number) {
    if (!confirm('Desactivar este usuario?')) return;
    try {
      await deleteUsuario(id);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al desactivar');
    }
  }

  const columns = [
    { key: 'id', header: 'ID' },
    { key: 'email', header: 'Email' },
    {
      key: 'nombre_completo',
      header: 'Nombre',
      render: (item: Usuario) => `${item.nombre} ${item.apellido}`,
    },
    {
      key: 'rol',
      header: 'Rol',
      render: (item: Usuario) => (
        <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
          {ROL_LABEL[item.rol] ?? item.rol}
        </span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      render: (item: Usuario) => <StatusBadge status={item.estado} />,
    },
    {
      key: 'acciones',
      header: 'Acciones',
      render: (item: Usuario) => (
        <div className="flex gap-2">
          <button
            onClick={() => openEdit(item)}
            className="rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400"
          >
            Editar
          </button>
          {item.estado === 'activo' && (
            <button
              onClick={() => handleDeactivate(item.id)}
              className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-400"
            >
              Desactivar
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Usuarios
        </h1>
        <button
          onClick={() => (showForm ? setShowForm(false) : openCreate())}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {showForm ? 'Cancelar' : 'Nuevo Usuario'}
        </button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
          <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-white">
            {editingId ? 'Editar Usuario' : 'Nuevo Usuario'}
          </h2>
          <form
            onSubmit={handleSubmit}
            className="grid grid-cols-1 gap-4 sm:grid-cols-2"
          >
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Email
              </label>
              <input
                type="email"
                value={formEmail}
                onChange={(e) => setFormEmail(e.target.value)}
                required={!editingId}
                disabled={!!editingId}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50 dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Rol
              </label>
              <select
                value={formRol}
                onChange={(e) => setFormRol(e.target.value)}
                required
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROL_LABEL[r]}
                  </option>
                ))}
              </select>
            </div>
            <div>
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
                Apellido
              </label>
              <input
                type="text"
                value={formApellido}
                onChange={(e) => setFormApellido(e.target.value)}
                required
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                {editingId
                  ? 'Nueva Contrasena (dejar vacio para no cambiar)'
                  : 'Contrasena'}
              </label>
              <input
                type="password"
                value={formPassword}
                onChange={(e) => setFormPassword(e.target.value)}
                required={!editingId}
                minLength={6}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
              />
            </div>
            <div className="flex gap-3 sm:col-span-2">
              <button
                type="submit"
                disabled={saving}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Guardando...' : editingId ? 'Actualizar' : 'Crear'}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="mb-4">
        <span className="text-sm text-zinc-500">
          {usuarios.length} usuarios
        </span>
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
          data={usuarios}
          keyExtractor={(u) => u.id}
        />
      )}
    </div>
  );
}
