import type { AuthenticatedUser } from '../types/auth'

let authToken: string | null = null

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function setApiAuthToken(token: string | null) {
  authToken = token
}

async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)

  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`)
  }

  return fetch(path, {
    ...init,
    headers,
  })
}

export async function fetchCurrentUser() {
  const response = await apiFetch('/api/v1/auth/me')

  if (!response.ok) {
    const message =
      response.status === 401 || response.status === 403
        ? 'Não foi possível validar sua sessão no backend.'
        : `Falha ao carregar o usuário autenticado (${response.status}).`

    throw new ApiError(message, response.status)
  }

  return (await response.json()) as AuthenticatedUser
}
