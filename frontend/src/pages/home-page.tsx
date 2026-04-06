import { useEffect, useState } from 'react'

type HealthState =
  | { status: 'loading' }
  | { status: 'success'; backendStatus: string }
  | { status: 'error'; message: string }

export function HomePage() {
  const [health, setHealth] = useState<HealthState>({ status: 'loading' })

  useEffect(() => {
    let active = true

    async function loadHealth() {
      try {
        const response = await fetch('/api/health')

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data = (await response.json()) as { status?: string }

        if (!active) {
          return
        }

        setHealth({
          status: 'success',
          backendStatus: data.status ?? 'unknown',
        })
      } catch (error) {
        if (!active) {
          return
        }

        setHealth({
          status: 'error',
          message:
            error instanceof Error ? error.message : 'Unexpected request error',
        })
      }
    }

    void loadHealth()

    return () => {
      active = false
    }
  }, [])

  return (
    <main className="min-h-screen px-6 py-10 text-slate-900 sm:px-10 lg:px-12">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl flex-col justify-between gap-12 rounded-[2rem] border border-emerald-950/10 bg-white/70 p-8 shadow-[0_24px_80px_rgba(27,67,50,0.12)] backdrop-blur md:p-12">
        <section className="grid gap-10 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-8">
            <div className="inline-flex items-center rounded-full border border-emerald-900/10 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-900">
              Daton ESG · Frontend skeleton · US-1.4
            </div>

            <div className="space-y-5">
              <p className="max-w-2xl text-sm font-semibold uppercase tracking-[0.24em] text-emerald-800/70">
                Worton ESG Report Generator
              </p>
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl lg:text-6xl">
                Base inicial do frontend para operar projetos, documentos e
                relatórios ESG.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-700">
                Esta tela é um placeholder técnico do monorepo. Ela valida o
                bootstrap com React 19, TypeScript, React Router, Tailwind e o
                proxy local para a API FastAPI.
              </p>
            </div>
          </div>

          <aside className="flex flex-col justify-between gap-6 rounded-[1.75rem] border border-emerald-900/10 bg-slate-950 px-6 py-7 text-slate-50">
            <div className="space-y-4">
              <p className="text-sm uppercase tracking-[0.22em] text-emerald-300">
                Backend connectivity
              </p>
              <div className="space-y-3">
                <p className="text-2xl font-semibold">
                  {health.status === 'loading' && 'Checking /api/health'}
                  {health.status === 'success' && 'API reachable'}
                  {health.status === 'error' && 'API unavailable'}
                </p>
                <p className="text-sm leading-6 text-slate-300">
                  {health.status === 'loading' &&
                    'The frontend is calling the backend through the Vite proxy.'}
                  {health.status === 'success' &&
                    `The backend answered with status "${health.backendStatus}".`}
                  {health.status === 'error' &&
                    `The health check failed through the proxy: ${health.message}.`}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
              <p className="font-medium text-white">Expected local ports</p>
              <p className="mt-2">Frontend: 5173</p>
              <p>Backend: 8000</p>
              <p>Postgres: 5432</p>
              <p>LocalStack: 4566</p>
            </div>
          </aside>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <StatusCard
            title="Routing"
            description="React Router is mounted and the root route is wired to this placeholder page."
          />
          <StatusCard
            title="Styling"
            description="Tailwind is configured as the base styling system for the frontend."
          />
          <StatusCard
            title="Project layout"
            description="components, pages, hooks, services and types directories are available for the next stories."
          />
        </section>
      </div>
    </main>
  )
}

type StatusCardProps = {
  title: string
  description: string
}

function StatusCard({ title, description }: StatusCardProps) {
  return (
    <article className="rounded-[1.5rem] border border-slate-900/8 bg-emerald-50/55 p-5 shadow-sm">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-800/75">
        {title}
      </p>
      <p className="mt-3 text-base leading-7 text-slate-700">{description}</p>
    </article>
  )
}
