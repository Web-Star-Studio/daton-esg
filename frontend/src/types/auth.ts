export type AuthenticatedUser = {
  id: string
  cognito_sub: string | null
  email: string
  name: string | null
  role: 'admin' | 'consultant'
  created_at: string
}

export type AuthTokens = {
  accessToken: string | null
  idToken: string | null
}

export type PendingAuthChallenge = {
  type: 'NEW_PASSWORD_REQUIRED'
  email: string
}

export type AuthSignInResult =
  | {
      status: 'signed-in'
      tokens: AuthTokens
    }
  | {
      status: 'new-password-required'
      challenge: PendingAuthChallenge
    }
