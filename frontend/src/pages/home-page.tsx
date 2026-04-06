import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { SiteHeader } from '../components/site-header'

type HealthState =
  | { status: 'loading' }
  | { status: 'success'; backendStatus: string }
  | { status: 'error'; message: string }

export function HomePage() {
  const [health, setHealth] = useState<HealthState>({ status: 'loading' })

  useEffect(() => {
    let active = true
    const controller = new AbortController()

    async function loadHealth() {
      try {
        const response = await fetch('/health', {
          signal: controller.signal,
        })

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
        if (error instanceof DOMException && error.name === 'AbortError') {
          return
        }

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
      controller.abort()
    }
  }, [])

  return (
    <div className="min-h-screen bg-[#000000] text-white">
      <SiteHeader />

      <main>
        <section className="border-b border-white/10 bg-[#000000] px-6 pb-24 pt-28 sm:px-10 lg:px-12">
          <div className="mx-auto flex w-full max-w-[980px] flex-col gap-8">
            <p className="text-left text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/72">
              Worton ESG Report Generator
            </p>
            <div className="space-y-5">
              <h1 className="max-w-4xl text-left [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-[40px] font-semibold leading-[1.07] tracking-[-0.28px] text-white sm:text-[56px]">
                Acesso seguro para operar relatórios ESG com precisão editorial.
              </h1>
              <p className="max-w-2xl text-left text-[17px] font-normal leading-[1.47] tracking-[-0.374px] text-white/80">
                O Daton ESG centraliza autenticação, ingestão documental e
                geração de relatório em um ambiente único para consultores da
                Worton.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Link
                to="/login"
                className="apple-blue-button apple-focus-ring inline-flex min-h-11 items-center justify-center px-[15px] py-2 text-[17px] font-normal leading-[1]"
              >
                Entrar
              </Link>
              <a
                href="#platform-status"
                className="apple-focus-ring apple-pill-link inline-flex min-h-11 items-center justify-center border border-white/32 px-5 py-2 text-[17px] font-normal leading-[1] text-[#2997ff]"
              >
                Ver status &gt;
              </a>
            </div>
          </div>
        </section>

        <section
          id="platform-status"
          className="bg-[#f5f5f7] px-6 py-20 text-[#1d1d1f] sm:px-10 lg:px-12"
        >
          <div className="mx-auto grid w-full max-w-[1180px] gap-5 lg:grid-cols-[1.1fr_0.9fr]">
            <article className="rounded-lg bg-white px-7 py-8 shadow-[rgba(0,0,0,0.22)_3px_5px_30px_0px]">
              <p className="text-[14px] font-semibold uppercase leading-[1.29] tracking-[-0.224px] text-black/70">
                Frontend foundation
              </p>
              <h2 className="mt-4 max-w-3xl [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-[28px] font-normal leading-[1.14] tracking-[0.196px]">
                Base alinhada para autenticação, rotas protegidas e integração
                com o backend FastAPI.
              </h2>
              <p className="mt-4 max-w-2xl text-[17px] leading-[1.47] tracking-[-0.374px] text-black/80">
                A home continua pública, mas agora segue a mesma linguagem
                visual da futura experiência autenticada e aponta para a entrada
                do workspace.
              </p>
            </article>

            <article className="rounded-lg bg-[#1d1d1f] px-7 py-8 text-white shadow-[rgba(0,0,0,0.22)_3px_5px_30px_0px]">
              <p className="text-[14px] font-semibold uppercase leading-[1.29] tracking-[-0.224px] text-white/72">
                Backend connectivity
              </p>
              <p className="mt-4 [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-[28px] font-normal leading-[1.14] tracking-[0.196px]">
                {health.status === 'loading' && 'Checking /health'}
                {health.status === 'success' && 'API reachable'}
                {health.status === 'error' && 'API unavailable'}
              </p>
              <p className="mt-4 text-[17px] leading-[1.47] tracking-[-0.374px] text-white/80">
                {health.status === 'loading' &&
                  'The frontend is calling the backend through the Vite proxy.'}
                {health.status === 'success' &&
                  `The backend answered with status "${health.backendStatus}".`}
                {health.status === 'error' &&
                  `The health check failed through the proxy: ${health.message}.`}
              </p>

              <div className="mt-8 grid gap-3 text-[14px] leading-[1.29] tracking-[-0.224px] text-white/72">
                <p>Frontend · 5173</p>
                <p>Backend · 8000</p>
                <p>Postgres · 5432</p>
                <p>LocalStack · 4566</p>
              </div>
            </article>
          </div>
        </section>

        <section className="bg-[#000000] px-6 py-20 sm:px-10 lg:px-12">
          <div className="mx-auto grid w-full max-w-[1180px] gap-4 md:grid-cols-3">
            <StatusCard
              title="Routing"
              description="React Router now supports public and protected flows, including /login and /dashboard."
            />
            <StatusCard
              title="Authentication"
              description="AWS Cognito can be wired into the SPA through Amplify with runtime tokens kept in memory."
            />
            <StatusCard
              title="Backend sync"
              description="Authenticated sessions normalize consultant identity through GET /api/v1/auth/me."
            />
          </div>
        </section>
      </main>
    </div>
  )
}

type StatusCardProps = {
  title: string
  description: string
}

function StatusCard({ title, description }: StatusCardProps) {
  return (
    <article className="rounded-lg bg-[#272729] px-6 py-7 shadow-[rgba(0,0,0,0.22)_3px_5px_30px_0px]">
      <p className="text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/72">
        {title}
      </p>
      <p className="mt-3 text-[17px] leading-[1.47] tracking-[-0.374px] text-white/84">
        {description}
      </p>
    </article>
  )
}
