import { useEffect, useState, type ReactNode } from 'react'
import {
  ApiError,
  fetchCurrentUser,
  setApiAuthToken,
} from '../services/api-client'
import {
  getCurrentAuthTokens,
  isAmplifyAuthConfigured,
  signInWithEmailPassword,
  signOutFromCognito,
} from '../services/amplify-auth'
import { AuthContext } from '../hooks/auth-context'
import type { AuthenticatedUser, AuthTokens } from '../types/auth'

function normalizeAuthError(error: unknown) {
  if (error instanceof ApiError) {
    return error
  }

  if (error instanceof Error) {
    const knownCognitoErrors = new Set([
      'NotAuthorizedException',
      'UserNotFoundException',
      'AuthValidationError',
    ])

    if (knownCognitoErrors.has(error.name)) {
      return new Error('Email ou senha inválidos.')
    }

    return error
  }

  return new Error('Não foi possível autenticar sua conta.')
}

function getBearerToken(tokens: AuthTokens) {
  return tokens.idToken ?? tokens.accessToken
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [idToken, setIdToken] = useState<string | null>(null)
  const [user, setUser] = useState<AuthenticatedUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true

    async function restoreSession() {
      if (!isAmplifyAuthConfigured()) {
        setApiAuthToken(null)
        if (active) {
          setAccessToken(null)
          setIdToken(null)
          setUser(null)
          setIsLoading(false)
        }
        return
      }

      try {
        const tokens = await getCurrentAuthTokens()
        const bearerToken = getBearerToken(tokens)

        if (!bearerToken) {
          setApiAuthToken(null)
          if (active) {
            setAccessToken(null)
            setIdToken(null)
            setUser(null)
            setIsLoading(false)
          }
          return
        }

        setApiAuthToken(bearerToken)
        const currentUser = await fetchCurrentUser()

        if (!active) {
          return
        }

        setAccessToken(tokens.accessToken)
        setIdToken(tokens.idToken)
        setUser(currentUser)
      } catch {
        setApiAuthToken(null)

        if (!active) {
          return
        }

        setAccessToken(null)
        setIdToken(null)
        setUser(null)
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    void restoreSession()

    return () => {
      active = false
    }
  }, [])

  async function login(email: string, password: string) {
    setIsLoading(true)

    try {
      const tokens = await signInWithEmailPassword(email, password)
      const bearerToken = getBearerToken(tokens)

      if (!bearerToken) {
        throw new Error('O Cognito não retornou um token utilizável.')
      }

      setApiAuthToken(bearerToken)
      const currentUser = await fetchCurrentUser()

      setAccessToken(tokens.accessToken)
      setIdToken(tokens.idToken)
      setUser(currentUser)
    } catch (error) {
      setApiAuthToken(null)
      setAccessToken(null)
      setIdToken(null)
      setUser(null)
      throw normalizeAuthError(error)
    } finally {
      setIsLoading(false)
    }
  }

  async function logout() {
    setIsLoading(true)

    try {
      if (isAmplifyAuthConfigured()) {
        await signOutFromCognito()
      }
    } finally {
      setApiAuthToken(null)
      setAccessToken(null)
      setIdToken(null)
      setUser(null)
      setIsLoading(false)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        idToken,
        isAuthenticated: user !== null,
        isLoading,
        login,
        logout,
        user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
