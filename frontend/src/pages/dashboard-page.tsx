import { SiteHeader } from '../components/site-header'
import { useAuth } from '../hooks/use-auth'

export function DashboardPage() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-[#f5f5f7] text-[#1d1d1f]">
      <SiteHeader />

      <main className="px-6 pb-20 pt-20 sm:px-10 lg:px-12">
        <div className="mx-auto grid w-full max-w-[1180px] gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-lg bg-white px-8 py-9 shadow-[rgba(0,0,0,0.22)_3px_5px_30px_0px]">
            <p className="text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-black/72">
              Dashboard
            </p>
            <h1 className="mt-4 max-w-[12ch] [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-[40px] font-semibold leading-[1.1] tracking-normal sm:text-[48px]">
              Workspace liberado.
            </h1>
            <p className="mt-4 max-w-[44ch] text-[17px] leading-[1.47] tracking-[-0.374px] text-black/80">
              Esta rota protegida fecha o fluxo inicial de autenticação da SPA.
              Nas próximas stories ela passa a hospedar projetos, documentos e
              geração de relatórios.
            </p>
          </section>

          <aside className="rounded-lg bg-[#1d1d1f] px-8 py-9 text-white shadow-[rgba(0,0,0,0.22)_3px_5px_30px_0px]">
            <p className="text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/72">
              Sessão autenticada
            </p>
            <dl className="mt-6 space-y-5 text-left">
              <div>
                <dt className="text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/64">
                  Nome
                </dt>
                <dd className="mt-2 text-[21px] font-normal leading-[1.19] tracking-[0.231px]">
                  {user?.name ?? 'Sem nome no Cognito'}
                </dd>
              </div>
              <div>
                <dt className="text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/64">
                  Email
                </dt>
                <dd className="mt-2 text-[17px] leading-[1.47] tracking-[-0.374px] text-white/84">
                  {user?.email}
                </dd>
              </div>
              <div>
                <dt className="text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/64">
                  Perfil
                </dt>
                <dd className="mt-2 text-[17px] leading-[1.47] tracking-[-0.374px] text-white/84">
                  {user?.role}
                </dd>
              </div>
            </dl>
          </aside>
        </div>
      </main>
    </div>
  )
}
