import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { SiteHeader } from '../components/site-header'
import { useAuth } from '../hooks/use-auth'
import { isAmplifyAuthConfigured } from '../services/amplify-auth'

type LocationState = {
  from?: string
}

export function LoginPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated, isLoading, login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate])

  const state = location.state as LocationState | null
  const intendedRoute =
    state?.from && state.from.startsWith('/') ? state.from : '/dashboard'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    try {
      await login(email.trim(), password)
      navigate(intendedRoute, { replace: true })
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Não foi possível autenticar sua conta.'
      )
    }
  }

  return (
    <div className="min-h-screen bg-[#000000] text-white">
      <SiteHeader />

      <main className="grid min-h-[calc(100vh-48px)] lg:grid-cols-[1.08fr_0.92fr]">
        <section className="flex items-end border-b border-white/10 px-6 py-16 sm:px-10 lg:border-b-0 lg:border-r lg:border-white/10 lg:px-12 lg:py-20">
          <div className="mx-auto w-full max-w-[560px] space-y-6">
            <p className="text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/72">
              Worton consultant access
            </p>
            <h1 className="max-w-[10ch] [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-[40px] font-semibold leading-[1.07] tracking-[-0.28px] text-white sm:text-[56px]">
              Entre com sua conta Worton.
            </h1>
            <p className="max-w-[42ch] text-[17px] font-normal leading-[1.47] tracking-[-0.374px] text-white/80">
              Use o acesso provisionado no Amazon Cognito para entrar no
              workspace de projetos, documentos e relatórios ESG.
            </p>

            <div className="rounded-lg bg-[#272729] px-6 py-7 shadow-[rgba(0,0,0,0.22)_3px_5px_30px_0px]">
              <p className="text-[14px] font-semibold leading-[1.29] tracking-[-0.224px] text-white">
                Segurança
              </p>
              <p className="mt-3 text-[14px] leading-[1.43] tracking-[-0.224px] text-white/72">
                Sessão local em memória. O frontend sincroniza sua identidade
                com o backend via JWT do Cognito após autenticação bem-sucedida.
              </p>
            </div>
          </div>
        </section>

        <section className="bg-[#f5f5f7] px-6 py-16 text-[#1d1d1f] sm:px-10 lg:px-12 lg:py-20">
          <div className="mx-auto w-full max-w-[460px]">
            <div className="rounded-lg bg-white px-7 py-8 shadow-[rgba(0,0,0,0.22)_3px_5px_30px_0px]">
              <p className="text-[14px] font-semibold uppercase leading-[1.29] tracking-[-0.224px] text-black/70">
                Login
              </p>
              <h2 className="mt-4 [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-[28px] font-normal leading-[1.14] tracking-[0.196px]">
                Acesse o workspace ESG.
              </h2>
              <p className="mt-3 text-[17px] leading-[1.47] tracking-[-0.374px] text-black/80">
                Insira seu email corporativo e a senha cadastrada no Cognito.
              </p>

              {!isAmplifyAuthConfigured() && (
                <div className="mt-6 rounded-lg bg-[#f5f5f7] px-4 py-4 text-[14px] leading-[1.43] tracking-[-0.224px] text-[#1d1d1f]">
                  Configure as variáveis `VITE_AWS_COGNITO_*` no arquivo `.env`
                  da raiz antes de usar o login real.
                </div>
              )}

              <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
                <label className="block text-left">
                  <span className="text-[14px] font-semibold leading-[1.29] tracking-[-0.224px] text-black/80">
                    Email
                  </span>
                  <input
                    type="email"
                    name="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => {
                      setEmail(event.target.value)
                    }}
                    className="apple-focus-ring mt-2 block min-h-11 w-full rounded-[11px] border border-black/10 bg-[#fafafc] px-4 text-[17px] leading-[1.47] tracking-[-0.374px] text-[#1d1d1f] placeholder:text-black/48"
                    placeholder="consultor@worton.com.br"
                    required
                  />
                </label>

                <label className="block text-left">
                  <span className="text-[14px] font-semibold leading-[1.29] tracking-[-0.224px] text-black/80">
                    Senha
                  </span>
                  <input
                    type="password"
                    name="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value)
                    }}
                    className="apple-focus-ring mt-2 block min-h-11 w-full rounded-[11px] border border-black/10 bg-[#fafafc] px-4 text-[17px] leading-[1.47] tracking-[-0.374px] text-[#1d1d1f] placeholder:text-black/48"
                    placeholder="Sua senha"
                    required
                  />
                </label>

                {error && (
                  <p
                    role="alert"
                    className="text-left text-[14px] leading-[1.43] tracking-[-0.224px] text-[#b3261e]"
                  >
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="apple-blue-button apple-focus-ring inline-flex min-h-11 w-full items-center justify-center px-[15px] py-2 text-[17px] font-normal leading-[1] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isLoading ? 'Validando acesso...' : 'Entrar com segurança'}
                </button>
              </form>

              <div className="mt-6 flex flex-wrap items-center gap-3 text-[14px] leading-[1.43] tracking-[-0.224px]">
                <Link
                  to="/"
                  className="apple-focus-ring apple-pill-link text-[#0066cc] hover:underline"
                >
                  Voltar para visão geral &gt;
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}
