import { useEffect, useState, type ReactNode } from 'react'
import {
  ApiError,
  fetchCurrentUser,
  setApiAuthToken,
} from '../services/api-client'
import {
  completeNewPasswordChallenge,
  getCurrentAuthTokens,
  isAmplifyAuthConfigured,
  signInWithEmailPassword,
  signOutFromCognito,
} from '../services/amplify-auth'
import { AuthContext } from '../hooks/auth-context'
import type {
  AuthenticatedUser,
  AuthTokens,
  PendingAuthChallenge,
} from '../types/auth'

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

    if (error.name === 'InvalidPasswordException') {
      return new Error(
        'A nova senha não atende à política configurada no Cognito.'
      )
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
  const [pendingChallenge, setPendingChallenge] =
    useState<PendingAuthChallenge | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true

    async function restoreSession() {
      if (!isAmplifyAuthConfigured()) {
        setApiAuthToken(null)
        if (active) {
          setAccessToken(null)
          setIdToken(null)
          setPendingChallenge(null)
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
            setPendingChallenge(null)
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
        setPendingChallenge(null)
        setUser(currentUser)
      } catch {
        setApiAuthToken(null)

        if (!active) {
          return
        }

        setAccessToken(null)
        setIdToken(null)
        setPendingChallenge(null)
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
    setPendingChallenge(null)

    try {
      const result = await signInWithEmailPassword(email, password)

      if (result.status === 'new-password-required') {
        setApiAuthToken(null)
        setAccessToken(null)
        setIdToken(null)
        setUser(null)
        setPendingChallenge(result.challenge)
        return
      }

      const tokens = result.tokens
      const bearerToken = getBearerToken(tokens)

      if (!bearerToken) {
        throw new Error('O Cognito não retornou um token utilizável.')
      }

      setApiAuthToken(bearerToken)
      const currentUser = await fetchCurrentUser()

      setAccessToken(tokens.accessToken)
      setIdToken(tokens.idToken)
      setPendingChallenge(null)
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

  async function completeNewPassword(newPassword: string) {
    setIsLoading(true)

    try {
      const tokens = await completeNewPasswordChallenge(newPassword)
      const bearerToken = getBearerToken(tokens)

      if (!bearerToken) {
        throw new Error('O Cognito não retornou um token utilizável.')
      }

      setApiAuthToken(bearerToken)
      const currentUser = await fetchCurrentUser()

      setAccessToken(tokens.accessToken)
      setIdToken(tokens.idToken)
      setPendingChallenge(null)
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
      setPendingChallenge(null)
      setUser(null)
      setIsLoading(false)
    }
  }

  function resetPendingChallenge() {
    setPendingChallenge(null)
  }

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        completeNewPassword,
        idToken,
        isAuthenticated: user !== null,
        isLoading,
        login,
        logout,
        pendingChallenge,
        resetPendingChallenge,
        user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
