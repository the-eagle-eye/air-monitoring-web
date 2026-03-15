'use client';

import { useEffect, useState } from 'react';
import AlertasTable from '@/components/alertas/AlertasTable';
import Badge from '@/components/ui/Badge';
import { fetchAlertas } from '@/lib/api/predicciones';
import type { Alerta } from '@/types/prediccion';

export default function AlertasPage() {
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [nivelFilter, setNivelFilter] = useState<string>('');
  const [estadoFilter, setEstadoFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pageSize = 50;

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAlertas({
      nivel_riesgo: nivelFilter || undefined,
      estado: estadoFilter || undefined,
      page,
      page_size: pageSize,
    })
      .then((data) => {
        setAlertas(data.items);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page, nivelFilter, estadoFilter]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Alertas
        </h1>
        <div className="flex items-center gap-3">
          <select
            value={nivelFilter}
            onChange={(e) => {
              setNivelFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          >
            <option value="">Todos los niveles</option>
            <option value="alta">Alta</option>
            <option value="media">Media</option>
            <option value="baja">Baja</option>
          </select>
          <select
            value={estadoFilter}
            onChange={(e) => {
              setEstadoFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          >
            <option value="">Todos los estados</option>
            <option value="activa">Activa</option>
            <option value="reconocida">Reconocida</option>
            <option value="resuelta">Resuelta</option>
          </select>
          <Badge label={`${total} alertas`} variant="info" />
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-zinc-400">Cargando...</div>
      ) : (
        <AlertasTable alertas={alertas} />
      )}

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-md bg-zinc-100 px-3 py-1.5 text-sm disabled:opacity-50 dark:bg-zinc-800"
          >
            Anterior
          </button>
          <span className="text-sm text-zinc-500">
            Pagina {page} de {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-md bg-zinc-100 px-3 py-1.5 text-sm disabled:opacity-50 dark:bg-zinc-800"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
}
