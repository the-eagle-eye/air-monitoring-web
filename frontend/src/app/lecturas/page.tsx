'use client';

import { useEffect, useState } from 'react';
import LecturasTable from '@/components/lecturas/LecturasTable';
import Badge from '@/components/ui/Badge';
import { fetchEquipos, fetchLecturas } from '@/lib/api/lecturas';
import type { Equipo, LecturaIoT } from '@/types/lectura';

export default function LecturasPage() {
  const [equipos, setEquipos] = useState<Equipo[]>([]);
  const [selectedEquipo, setSelectedEquipo] = useState<string>('');
  const [lecturas, setLecturas] = useState<LecturaIoT[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pageSize = 50;

  useEffect(() => {
    fetchEquipos()
      .then((data) => {
        setEquipos(data);
        if (data.length > 0) {
          setSelectedEquipo(data[0].device_id);
        }
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedEquipo) return;
    setLoading(true);
    setError(null);
    fetchLecturas(selectedEquipo, page, pageSize)
      .then((data) => {
        setLecturas(data.items);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedEquipo, page]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Lecturas IoT
        </h1>
        <div className="flex items-center gap-3">
          <label
            htmlFor="equipo-select"
            className="text-sm text-zinc-600 dark:text-zinc-400"
          >
            Equipo:
          </label>
          <select
            id="equipo-select"
            value={selectedEquipo}
            onChange={(e) => {
              setSelectedEquipo(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          >
            {equipos.map((eq) => (
              <option key={eq.device_id} value={eq.device_id}>
                {eq.device_id} — {eq.nombre ?? eq.tipo ?? 'Sin nombre'}
              </option>
            ))}
          </select>
          <Badge label={`${total} lecturas`} variant="info" />
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
        <LecturasTable lecturas={lecturas} />
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
