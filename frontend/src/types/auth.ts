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
