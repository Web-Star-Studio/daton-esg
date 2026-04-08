import { useEffect, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/use-auth'
import { isAmplifyAuthConfigured } from '../services/amplify-auth'

type LocationState = {
  from?: string
}

type PasswordFieldProps = {
  ariaLabel: string
  autoComplete: string
  name: string
  onChange: (value: string) => void
  placeholder: string
  value: string
}

function PasswordField({
  ariaLabel,
  autoComplete,
  name,
  onChange,
  placeholder,
  value,
}: PasswordFieldProps) {
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="relative">
      <label htmlFor={name} className="sr-only">
        {ariaLabel}
      </label>
      <input
        id={name}
        type={isVisible ? 'text' : 'password'}
        name={name}
        autoComplete={autoComplete}
        value={value}
        onChange={(event) => {
          onChange(event.target.value)
        }}
        className="apple-focus-ring h-12 w-full rounded border border-[#d2d2d7] bg-white px-4 pr-12 text-[17px] font-normal leading-[1.4] tracking-[-0.01em] text-[#1d1d1f] shadow-sm placeholder:text-[#86868b] focus:border-[#0071e3] focus:ring-4 focus:ring-[#0071e3]/20"
        placeholder={placeholder}
        required
      />
      <button
        type="button"
        onClick={() => {
          setIsVisible((current) => !current)
        }}
        className="apple-focus-ring absolute inset-y-0 right-0 flex items-center pr-3 text-[#86868b] transition-colors hover:text-[#1d1d1f]"
        aria-label={isVisible ? 'Ocultar senha' : 'Mostrar senha'}
      >
        <span aria-hidden="true" className="text-[20px] leading-none">
          {isVisible ? '◐' : '◌'}
        </span>
      </button>
    </div>
  )
}

export function LoginPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const {
    completeNewPassword,
    isAuthenticated,
    isLoading,
    login,
    logout,
    pendingChallenge,
    resetPendingChallenge,
  } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const isNewPasswordStep = pendingChallenge?.type === 'NEW_PASSWORD_REQUIRED'

  const state = location.state as LocationState | null
  const intendedRoute =
    state?.from && state.from.startsWith('/') ? state.from : '/dashboard'

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(intendedRoute, { replace: true })
    }
  }, [intendedRoute, isAuthenticated, isLoading, navigate])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    try {
      if (isNewPasswordStep) {
        if (newPassword !== confirmNewPassword) {
          setError('A confirmação da nova senha não confere.')
          return
        }

        await completeNewPassword(newPassword)
      } else {
        await login(email.trim(), password)
      }

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
    <main className="flex min-h-screen w-full flex-col overflow-x-hidden bg-[#f5f5f7] font-['SF_Pro_Text','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] antialiased selection:bg-[#0071e3] selection:text-white md:flex-row">
      <section className="relative hidden w-full flex-col justify-center overflow-hidden bg-black px-12 py-12 md:flex md:w-[40%] lg:w-[50%] lg:px-24">
        <div className="relative z-10 max-w-xl">
          <p className="mb-6 text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/48">
            Daton ESG
          </p>
          <h1 className="mb-6 [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-5xl font-semibold leading-[1.05] tracking-[-0.022em] text-white lg:text-[64px]">
            Sustentabilidade em escala. Medida com precisão.
          </h1>
          <p className="text-xl font-medium leading-[1.2] tracking-[-0.015em] text-[#86868b] lg:text-2xl">
            A plataforma de inteligência ESG para o futuro do planeta.
          </p>
        </div>
      </section>

      <section className="relative flex min-h-screen w-full flex-col items-center justify-center bg-[#f5f5f7] p-6 sm:p-12 md:w-[60%] lg:w-[50%]">
        <div className="absolute left-6 top-8 md:hidden">
          <span className="text-[12px] font-semibold uppercase tracking-[-0.12px] text-[#1d1d1f]/60">
            Daton ESG
          </span>
        </div>

        <div className="w-full max-w-[380px] bg-transparent">
          <div className="mb-10 text-center md:text-left">
            <p className="text-[14px] font-semibold uppercase leading-[1.29] tracking-[-0.224px] text-black/60">
              {isNewPasswordStep ? 'Nova senha' : 'Login'}
            </p>
            <h2 className="mt-4 [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-[32px] font-semibold leading-[1.1] tracking-[-0.01em] text-[#1d1d1f]">
              {isNewPasswordStep ? 'Defina sua nova senha' : 'Acesse sua conta'}
            </h2>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            {!isAmplifyAuthConfigured() && (
              <div className="rounded-xl bg-white px-4 py-4 text-[14px] leading-[1.43] tracking-[-0.224px] text-[#1d1d1f] shadow-sm">
                Configure as variáveis `VITE_AWS_COGNITO_*` no `.env` da raiz
                antes de usar o login real.
              </div>
            )}

            <div>
              <label htmlFor="email" className="sr-only">
                E-mail corporativo
              </label>
              <input
                id="email"
                type="email"
                name="email"
                autoComplete="email"
                value={pendingChallenge?.email ?? email}
                onChange={(event) => {
                  setEmail(event.target.value)
                }}
                readOnly={isNewPasswordStep}
                className="apple-focus-ring h-12 w-full rounded border border-[#d2d2d7] bg-white px-4 text-[17px] font-normal leading-[1.4] tracking-[-0.01em] text-[#1d1d1f] shadow-sm placeholder:text-[#86868b] focus:border-[#0071e3] focus:ring-4 focus:ring-[#0071e3]/20 read-only:cursor-not-allowed read-only:bg-[#f5f5f7]"
                placeholder="E-mail corporativo"
                required
              />
            </div>

            {isNewPasswordStep ? (
              <>
                <div className="rounded-xl bg-white/75 px-4 py-4 text-[14px] leading-[1.43] tracking-[-0.224px] text-[#1d1d1f]">
                  O Cognito validou sua senha temporária. Defina uma nova senha
                  para concluir a autenticação.
                </div>
                <div>
                  <PasswordField
                    ariaLabel="Nova senha"
                    autoComplete="new-password"
                    name="new-password"
                    onChange={setNewPassword}
                    placeholder="Nova senha"
                    value={newPassword}
                  />
                </div>
                <div>
                  <PasswordField
                    ariaLabel="Confirmar nova senha"
                    autoComplete="new-password"
                    name="confirm-new-password"
                    onChange={setConfirmNewPassword}
                    placeholder="Confirmar nova senha"
                    value={confirmNewPassword}
                  />
                </div>
              </>
            ) : (
              <div>
                <PasswordField
                  ariaLabel="Senha"
                  autoComplete="current-password"
                  name="password"
                  onChange={setPassword}
                  placeholder="Senha"
                  value={password}
                />
              </div>
            )}

            {error && (
              <p
                role="alert"
                className="text-[14px] font-normal leading-[1.43] tracking-[-0.01em] text-[#d01f1f]"
              >
                {error}
              </p>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="apple-focus-ring flex h-12 w-full items-center justify-center rounded-lg bg-[#0673e0] text-[17px] font-medium tracking-[-0.01em] text-white shadow-sm transition-all duration-200 ease-in-out hover:bg-blue-600 focus:ring-4 focus:ring-[#0673e0]/30 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoading
                  ? isNewPasswordStep
                    ? 'Atualizando senha...'
                    : 'Validando acesso...'
                  : isNewPasswordStep
                    ? 'Definir nova senha'
                    : 'Entrar'}
              </button>
            </div>

            <div className="flex items-center justify-center pt-4">
              {isNewPasswordStep ? (
                <button
                  type="button"
                  onClick={() => {
                    resetPendingChallenge()
                    void logout()
                    navigate('/login', { replace: true })
                  }}
                  className="apple-focus-ring text-[14px] font-medium tracking-normal text-[#0673e0] transition-colors hover:text-blue-700 hover:underline"
                >
                  Voltar para o login &gt;
                </button>
              ) : (
                <button
                  type="button"
                  className="apple-focus-ring text-[14px] font-medium tracking-normal text-[#0673e0] transition-colors hover:text-blue-700 hover:underline"
                >
                  Esqueceu a senha?
                </button>
              )}
            </div>
          </form>
        </div>

        <div className="absolute bottom-6 w-full px-6 text-center">
          <p className="text-[12px] tracking-normal text-[#86868b]">
            Protegido por reCAPTCHA e sujeito à{' '}
            <a className="underline hover:text-[#1d1d1f]" href="#">
              Política de Privacidade
            </a>
            .
          </p>
        </div>
      </section>
    </main>
  )
}
