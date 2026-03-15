'use client';

import { useRouter } from 'next/navigation';
import EquipoForm from '@/components/equipos/EquipoForm';
import { createEquipo } from '@/lib/api/lecturas';

export default function NuevoEquipoPage() {
  const router = useRouter();

  async function handleSubmit(data: Record<string, unknown>) {
    await createEquipo(data as { device_id: string });
    router.push('/equipos');
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold text-zinc-900 dark:text-white">
        Nuevo Equipo
      </h1>
      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900">
        <EquipoForm
          mode="create"
          onSubmit={handleSubmit}
          onCancel={() => router.push('/equipos')}
        />
      </div>
    </div>
  );
}
