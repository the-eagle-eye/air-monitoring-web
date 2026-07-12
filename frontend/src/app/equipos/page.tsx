'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { fetchEquipos } from '@/lib/api/lecturas';
import { useAuth } from '@/lib/auth';
import EquiposTable from '@/components/equipos/EquiposTable';
import EquiposPendientes from '@/components/equipos/EquiposPendientes';
import type { Equipo } from '@/types/lectura';

export default function EquiposPage() {
  const [equipos, setEquipos] = useState<Equipo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  const canEdit = user?.rol === 'administrador';
  // C8: confirmar equipos en cuarentena = coordinador/admin
  const canConfirm =
    user?.rol === 'coordinador' || user?.rol === 'administrador';

  const loadEquipos = useCallback(() => {
    fetchEquipos()
      .then(setEquipos)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadEquipos();
  }, [loadEquipos]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Equipos
        </h1>
        {canEdit && (
          <Link
            href="/equipos/nuevo"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Nuevo Equipo
          </Link>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {canConfirm && (
        <EquiposPendientes canConfirm={canConfirm} onConfirmed={loadEquipos} />
      )}

      {loading ? (
        <div className="py-12 text-center text-zinc-400">Cargando...</div>
      ) : (
        <EquiposTable equipos={equipos} readOnly={!canEdit} />
      )}
    </div>
  );
}
