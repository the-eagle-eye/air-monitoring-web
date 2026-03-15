export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
      <main className="flex flex-col items-center gap-8 text-center">
        <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-50">
          Sistema de Monitoreo Predictivo
        </h1>
        <p className="max-w-md text-lg text-zinc-600 dark:text-zinc-400">
          Plataforma de monitoreo predictivo para equipos de medicion de calidad
          de aire
        </p>
        <div className="flex gap-4 text-sm text-zinc-500">
          <span className="rounded-full bg-green-100 px-3 py-1 text-green-800">
            IoT Service
          </span>
          <span className="rounded-full bg-blue-100 px-3 py-1 text-blue-800">
            ML Service
          </span>
          <span className="rounded-full bg-purple-100 px-3 py-1 text-purple-800">
            Ops Service
          </span>
        </div>
      </main>
    </div>
  );
}
