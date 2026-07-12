'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  fetchReincidentes,
  fetchProblemasResumen,
  createProblema,
  linkIncidenciaProblema,
  type EquipoReincidente,
} from '@/lib/api/ops';

// ITIL — Gestión de Problemas hecha VISIBLE y PROACTIVA.
// El sistema detecta equipos con correctivas recurrentes (>=3 en 90d por defecto)
// y SUGIERE abrir un Problema (causa raíz). El coordinador confirma con un clic:
// se crea el Problema pre-llenado y se vinculan automáticamente esas incidencias.
// No crea nada automáticamente — un Problema implica análisis humano de la causa.
export default function EquiposReincidentes({
  canCrear,
  onProblemaCreado,
}: {
  canCrear: boolean;
  onProblemaCreado?: () => void;
}) {
  const [items, setItems] = useState<EquipoReincidente[]>([]);
  const [abiertos, setAbiertos] = useState(0);
  const [loading, setLoading] = useState(true);
  const [creando, setCreando] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([fetchReincidentes(), fetchProblemasResumen()])
      .then(([rein, resumen]) => {
        setItems(rein.items);
        setAbiertos(resumen.abiertos);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCrear(eq: EquipoReincidente) {
    setCreando(eq.device_id);
    setMensaje(null);
    try {
      // 1) crear el Problema pre-llenado con el equipo y un título sugerido
      const problema = await createProblema({
        device_id: eq.device_id,
        titulo: `Correctivas recurrentes en ${eq.device_id} (${eq.correctivas} en 90 días)`,
        descripcion:
          `Detectado automáticamente: ${eq.correctivas} incidencias correctivas ` +
          `para ${eq.device_id} en los últimos 90 días. Investigar causa raíz.`,
      });
      // 2) vincular las incidencias recurrentes al nuevo Problema
      await Promise.all(
        eq.incidencia_ids.map((id) => linkIncidenciaProblema(id, problema.id)),
      );
      setItems((prev) => prev.filter((i) => i.device_id !== eq.device_id));
      setMensaje(
        `Problema #${problema.id} creado para ${eq.device_id} con ${eq.incidencia_ids.length} incidencias vinculadas`,
      );
      onProblemaCreado?.();
    } catch {
      setMensaje('No se pudo crear el problema; reintenta');
      load();
    } finally {
      setCreando(null);
    }
  }

  if (loading) return null;

  // Si no hay reincidentes NI problemas abiertos, mostramos un estado informativo
  // discreto para que la sección exista y se entienda (visibilidad).
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Problemas (causa raíz)
        </h2>
        <Link
          href="/problemas"
          className="text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          {abiertos > 0
            ? `${abiertos} abierto${abiertos > 1 ? 's' : ''} →`
            : 'Ver todos →'}
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="flex h-[120px] flex-col items-center justify-center gap-1 text-center text-sm text-zinc-400">
          <span>Sin equipos con correctivas recurrentes.</span>
          <span className="text-xs">
            Se sugerirá abrir un problema si un equipo acumula ≥3 correctivas en
            90 días.
          </span>
        </div>
      ) : (
        <>
          <p className="mb-2 text-xs text-amber-700 dark:text-amber-400">
            ⚠️ Equipos con fallas recurrentes — considera abrir un problema para
            investigar la causa raíz:
          </p>
          <div className="space-y-2">
            {items.map((eq) => (
              <div
                key={eq.device_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-800/40 dark:bg-amber-900/20"
              >
                <div className="flex items-center gap-2">
                  <Link
                    href={`/equipos/${eq.device_id}`}
                    className="font-mono text-sm font-medium text-zinc-900 hover:underline dark:text-zinc-100"
                  >
                    {eq.device_id}
                  </Link>
                  <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                    {eq.correctivas} correctivas / 90d
                  </span>
                </div>
                {canCrear && (
                  <button
                    onClick={() => handleCrear(eq)}
                    disabled={creando === eq.device_id}
                    className="rounded-md bg-amber-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                  >
                    {creando === eq.device_id ? 'Creando...' : 'Crear problema'}
                  </button>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {mensaje && (
        <p className="mt-3 text-xs font-medium text-green-600 dark:text-green-400">
          {mensaje}
        </p>
      )}
    </div>
  );
}
