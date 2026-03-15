'use client';

import { useEffect, useState } from 'react';
import PrediccionCard from '@/components/predicciones/PrediccionCard';
import PrediccionesTable from '@/components/predicciones/PrediccionesTable';
import { fetchEquipos } from '@/lib/api/lecturas';
import { fetchPredicciones, runPredictions } from '@/lib/api/predicciones';
import type { Equipo } from '@/types/lectura';
import type { Prediccion } from '@/types/prediccion';

export default function PrediccionesPage() {
  const [equipos, setEquipos] = useState<Equipo[]>([]);
  const [selectedEquipo, setSelectedEquipo] = useState<string>('');
  const [latest, setLatest] = useState<Prediccion | null>(null);
  const [historial, setHistorial] = useState<Prediccion[]>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEquipos()
      .then((data) => {
        setEquipos(data);
        if (data.length > 0) setSelectedEquipo(data[0].device_id);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedEquipo) return;
    setLoading(true);
    setError(null);
    fetchPredicciones(selectedEquipo)
      .then((data) => {
        setHistorial(data.items);
        setLatest(data.items[0] ?? null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedEquipo]);

  const handleRunPrediction = async () => {
    setRunning(true);
    setError(null);
    try {
      const results = await runPredictions(selectedEquipo);
      if (results.length > 0) {
        setLatest(results[0]);
        // Refresh history
        const data = await fetchPredicciones(selectedEquipo);
        setHistorial(data.items);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error ejecutando prediccion');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
          Predicciones
        </h1>
        <div className="flex items-center gap-3">
          <select
            value={selectedEquipo}
            onChange={(e) => setSelectedEquipo(e.target.value)}
            className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
          >
            {equipos.map((eq) => (
              <option key={eq.device_id} value={eq.device_id}>
                {eq.device_id} — {eq.nombre ?? eq.tipo ?? 'Sin nombre'}
              </option>
            ))}
          </select>
          <button
            onClick={handleRunPrediction}
            disabled={running || !selectedEquipo}
            className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {running ? 'Ejecutando...' : 'Ejecutar Prediccion'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {latest && (
        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <PrediccionCard prediccion={latest} />
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-zinc-400">Cargando...</div>
      ) : (
        <>
          <h2 className="mb-3 text-lg font-semibold text-zinc-800 dark:text-zinc-200">
            Historial
          </h2>
          <PrediccionesTable predicciones={historial} />
        </>
      )}
    </div>
  );
}
