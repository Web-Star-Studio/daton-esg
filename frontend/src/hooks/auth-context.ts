import { createContext } from 'react'
import type { AuthenticatedUser, PendingAuthChallenge } from '../types/auth'

export type AuthContextValue = {
  accessToken: string | null
  idToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  pendingChallenge: PendingAuthChallenge | null
  login: (email: string, password: string) => Promise<void>
  completeNewPassword: (newPassword: string) => Promise<void>
  logout: () => Promise<void>
  user: AuthenticatedUser | null
}

export const AuthContext = createContext<AuthContextValue | null>(null)
