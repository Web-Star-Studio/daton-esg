import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/use-auth'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#000000] px-6 text-white">
        <div className="w-full max-w-[420px] rounded-lg bg-[#1d1d1f] px-8 py-10 text-left shadow-[rgba(0,0,0,0.22)_3px_5px_30px_0px]">
          <p className="text-[12px] font-semibold uppercase leading-[1.33] tracking-[-0.12px] text-white/72">
            Authentication
          </p>
          <p className="mt-3 [font-family:'SF_Pro_Display','SF_Pro_Icons','Helvetica_Neue',Helvetica,Arial,sans-serif] text-[28px] font-normal leading-[1.14] tracking-[0.196px]">
            Validando sessão.
          </p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    )
  }

  return children
}
