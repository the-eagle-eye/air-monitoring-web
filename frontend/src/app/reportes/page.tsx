'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { fetchReportePreview, downloadReporte } from '@/lib/api/ops';
import DataTable from '@/components/ui/DataTable';
import type { ReporteRow } from '@/types/ops';

const PRIORIDAD_COLORS: Record<string, string> = {
  alta: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  media: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  baja: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

export default function ReportesPage() {
  const { user } = useAuth();
  const canAccess =
    user?.rol === 'administrador' || user?.rol === 'coordinador';

  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [tipo, setTipo] = useState('');
  const [deviceId, setDeviceId] = useState('');

  const [rows, setRows] = useState<ReporteRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);

  if (!canAccess) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          No tiene permisos para acceder a esta seccion.
        </div>
      </div>
    );
  }

  const params = {
    fecha_inicio: fechaInicio || undefined,
    fecha_fin: fechaFin || undefined,
    tipo: tipo || undefined,
    device_id: deviceId || undefined,
  };

  async function handleSearch() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReportePreview(params);
      setRows(data.items);
      setTotal(data.total);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar reporte');
    } finally {
      setLoading(false);
    }
  }

  async function handleExport(format: 'csv' | 'pdf') {
    setExporting(format);
    setError(null);
    try {
      await downloadReporte(format, params);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al exportar');
    } finally {
      setExporting(null);
    }
  }

  const columns = [
    { key: 'id_incidencia', header: 'ID' },
    { key: 'device_id', header: 'Equipo' },
    {
      key: 'tipo',
      header: 'Tipo',
      render: (item: ReporteRow) => (
        <span className="inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
          {item.tipo}
        </span>
      ),
    },
    { key: 'estado', header: 'Estado' },
    {
      key: 'prioridad',
      header: 'Prioridad',
      render: (item: ReporteRow) => (
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${PRIORIDAD_COLORS[item.prioridad] || ''}`}
        >
          {item.prioridad}
        </span>
      ),
    },
    { key: 'responsable', header: 'Responsable' },
    {
      key: 'fecha_creacion',
      header: 'Fecha',
      render: (item: ReporteRow) =>
        item.fecha_creacion
          ? new Date(item.fecha_creacion).toLocaleDateString()
          : '—',
    },
    {
      key: 'detalle',
      header: 'Detalle',
      render: (item: ReporteRow) => {
        if (item.tipo === 'correctiva' && item.diagnostico) {
          return (
            <span className="text-xs" title={item.diagnostico}>
              {item.diagnostico.length > 50
                ? item.diagnostico.slice(0, 50) + '...'
                : item.diagnostico}
            </span>
          );
        }
        if (item.tipo === 'calibracion' && item.nota_calibracion) {
          return (
            <span className="text-xs" title={item.nota_calibracion}>
              {item.nota_calibracion.length > 50
                ? item.nota_calibracion.slice(0, 50) + '...'
                : item.nota_calibracion}
            </span>
          );
        }
        return <span className="text-xs text-zinc-400">—</span>;
      },
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold text-zinc-900 dark:text-white">
        Reportes de Auditoria
      </h1>

      {/* Filters */}
      <div className="mb-6 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Fecha Inicio
            </label>
            <input
              type="date"
              value={fechaInicio}
              onChange={(e) => setFechaInicio(e.target.value)}
              className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Fecha Fin
            </label>
            <input
              type="date"
              value={fechaFin}
              onChange={(e) => setFechaFin(e.target.value)}
              className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Tipo
            </label>
            <select
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
              className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            >
              <option value="">Todos</option>
              <option value="correctiva">Correctiva</option>
              <option value="calibracion">Calibracion</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Equipo (ID)
            </label>
            <input
              type="text"
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              placeholder="Ej: T101"
              className="w-28 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Buscando...' : 'Buscar'}
          </button>
        </div>
      </div>

      {/* Export buttons */}
      {searched && (
        <div className="mb-4 flex items-center gap-3">
          <span className="text-sm text-zinc-500 dark:text-zinc-400">
            {total} registro{total !== 1 ? 's' : ''} encontrado{total !== 1 ? 's' : ''}
          </span>
          <div className="ml-auto flex gap-2">
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting !== null}
              className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-50"
            >
              {exporting === 'csv' ? 'Exportando...' : 'Exportar CSV'}
            </button>
            <button
              onClick={() => handleExport('pdf')}
              disabled={exporting !== null}
              className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-50"
            >
              {exporting === 'pdf' ? 'Exportando...' : 'Exportar PDF'}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-zinc-400">Cargando...</div>
      ) : searched ? (
        <DataTable
          columns={columns}
          data={rows}
          keyExtractor={(r) => r.id_incidencia}
        />
      ) : (
        <div className="py-12 text-center text-zinc-400">
          Configure los filtros y presione Buscar para generar el reporte.
        </div>
      )}
    </div>
  );
}
