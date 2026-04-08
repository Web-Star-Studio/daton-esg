import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/use-auth'

export function SiteHeader() {
  const { isAuthenticated, logout, user } = useAuth()

  return (
    <header className="apple-nav sticky top-0 z-50 border-b border-white/10">
      <div className="mx-auto flex h-12 w-full max-w-[1180px] items-center justify-between px-6 sm:px-10 lg:px-12">
        <Link
          to={isAuthenticated ? '/dashboard' : '/login'}
          className="apple-focus-ring text-[12px] font-normal leading-[1.47] tracking-[-0.08px] text-white"
        >
          Daton ESG
        </Link>

        <nav className="flex items-center gap-4 text-[12px] font-normal leading-[1.47] tracking-[-0.08px] text-white/80">
          <Link to="/dashboard" className="apple-focus-ring hover:text-white">
            Dashboard
          </Link>
          {isAuthenticated ? (
            <>
              <span className="hidden text-white/64 sm:inline">
                {user?.name ?? user?.email}
              </span>
              <button
                type="button"
                onClick={() => {
                  void logout()
                }}
                className="apple-focus-ring inline-flex min-h-8 items-center rounded-[980px] border border-white/24 px-3 text-white hover:border-white/40"
              >
                Sair
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="apple-focus-ring inline-flex min-h-8 items-center rounded-[980px] border border-[#2997ff] px-3 text-[#2997ff] hover:underline"
            >
              Entrar &gt;
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}
