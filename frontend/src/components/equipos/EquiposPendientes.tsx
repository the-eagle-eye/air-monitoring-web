'use client';

import { useEffect, useState, useCallback } from 'react';
import { fetchEquiposPendientes, confirmarEquipo } from '@/lib/api/lecturas';
import type { Equipo } from '@/types/lectura';

// C8: panel de equipos en cuarentena (estado no_confirmado) que aparecieron solos
// al enviar lecturas. El coordinador/admin los confirma (activa) opcionalmente
// completando criticidad. Visible solo para roles con permiso de confirmar.
export default function EquiposPendientes({
  canConfirm,
  onConfirmed,
}: {
  canConfirm: boolean;
  onConfirmed?: () => void;
}) {
  const [pendientes, setPendientes] = useState<Equipo[]>([]);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [crit, setCrit] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    fetchEquiposPendientes()
      .then(setPendientes)
      .catch(() => setPendientes([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleConfirm(deviceId: string) {
    setConfirming(deviceId);
    try {
      await confirmarEquipo(deviceId, { criticidad: crit[deviceId] ?? 'media' });
      setPendientes((prev) => prev.filter((e) => e.device_id !== deviceId));
      onConfirmed?.();
    } catch {
      // el panel se recarga al fallar para reflejar el estado real
      load();
    } finally {
      setConfirming(null);
    }
  }

  if (loading || pendientes.length === 0) return null;

  return (
    <div className="mb-6 rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-700/50 dark:bg-amber-900/20">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-lg">🟡</span>
        <h2 className="text-sm font-semibold text-amber-800 dark:text-amber-300">
          Equipos por confirmar ({pendientes.length})
        </h2>
      </div>
      <p className="mb-3 text-xs text-amber-700 dark:text-amber-400">
        Estos equipos empezaron a enviar lecturas pero no estaban registrados. Se
        crearon en cuarentena. Confírmalos para activarlos (asigna su criticidad).
      </p>
      <div className="space-y-2">
        {pendientes.map((eq) => (
          <div
            key={eq.device_id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-amber-200 bg-white px-3 py-2 dark:border-amber-800/40 dark:bg-zinc-900"
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {eq.device_id}
              </span>
              <span className="text-xs text-zinc-400">
                detectado {new Date(eq.fecha_registro).toLocaleString()}
              </span>
            </div>
            {canConfirm ? (
              <div className="flex items-center gap-2">
                <label className="text-xs text-zinc-500 dark:text-zinc-400">Criticidad</label>
                <select
                  value={crit[eq.device_id] ?? 'media'}
                  onChange={(e) => setCrit((p) => ({ ...p, [eq.device_id]: e.target.value }))}
                  className="rounded border border-zinc-300 px-2 py-1 text-xs dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                >
                  <option value="baja">Baja</option>
                  <option value="media">Media</option>
                  <option value="alta">Alta</option>
                </select>
                <button
                  onClick={() => handleConfirm(eq.device_id)}
                  disabled={confirming === eq.device_id}
                  className="rounded-md bg-amber-600 px-3 py-1 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                >
                  {confirming === eq.device_id ? 'Confirmando...' : 'Confirmar'}
                </button>
              </div>
            ) : (
              <span className="text-xs text-zinc-400">Pendiente de aprobación</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
