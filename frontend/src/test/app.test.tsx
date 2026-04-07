import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import type { AuthContextValue } from '../hooks/auth-context'
import { useAuth } from '../hooks/use-auth'

vi.mock('../hooks/use-auth', () => ({
  useAuth: vi.fn(),
}))

type MockAuthState = AuthContextValue

const mockUseAuth = vi.mocked(useAuth)

function createAuthState(
  overrides: Partial<MockAuthState> = {}
): MockAuthState {
  return {
    accessToken: null,
    idToken: null,
    isAuthenticated: false,
    isLoading: false,
    user: null,
    login: vi.fn(async () => undefined) as MockAuthState['login'],
    logout: vi.fn(async () => undefined) as MockAuthState['logout'],
    ...overrides,
  }
}

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ status: 'ok' }),
      }))
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  function renderApp(path: string) {
    render(
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    )
  }

  it('renders the public home route', () => {
    mockUseAuth.mockReturnValue(createAuthState())

    renderApp('/')

    expect(
      screen.getByText(/acesso seguro para operar relatórios esg/i)
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^entrar$/i })).toBeInTheDocument()
  })

  it('renders the login page for unauthenticated users', () => {
    mockUseAuth.mockReturnValue(createAuthState())

    renderApp('/login')

    expect(
      screen.getByRole('heading', { name: /entre com sua conta worton/i })
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument()
  })

  it('redirects unauthenticated users from /dashboard to /login', async () => {
    mockUseAuth.mockReturnValue(createAuthState())

    renderApp('/dashboard')

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /entre com sua conta worton/i })
      ).toBeInTheDocument()
    })
  })

  it('redirects authenticated users away from /login', async () => {
    mockUseAuth.mockReturnValue(
      createAuthState({
        isAuthenticated: true,
        accessToken: 'access-token',
        idToken: 'id-token',
        user: {
          id: 'user-1',
          cognito_sub: 'cognito-sub-1',
          email: 'bruna@example.com',
          name: 'Bruna Souza',
          role: 'consultant',
          created_at: '2026-04-06T00:00:00Z',
        },
      })
    )

    renderApp('/login')

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /workspace liberado/i })
      ).toBeInTheDocument()
    })
  })

  it('shows an inline error when login fails', async () => {
    const login = vi.fn(async () => {
      throw new Error('Email ou senha inválidos.')
    })

    mockUseAuth.mockReturnValue(createAuthState({ login }))

    renderApp('/login')

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'consultor@example.com' },
    })
    fireEvent.change(screen.getByLabelText(/senha/i), {
      target: { value: 'SenhaErrada123!' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: /entrar com segurança/i })
    )

    await waitFor(() => {
      expect(screen.getByText(/email ou senha inválidos/i)).toBeInTheDocument()
    })
  })

  it('disables the submit button and shows loading copy while auth is loading', () => {
    mockUseAuth.mockReturnValue(
      createAuthState({
        isLoading: true,
      })
    )

    renderApp('/login')

    const submitButton = screen.getByRole('button', {
      name: /validando acesso/i,
    })

    expect(submitButton).toBeDisabled()
    expect(screen.getByText(/validando acesso/i)).toBeInTheDocument()
  })

  it('redirects to /dashboard after successful login', async () => {
    const authState = createAuthState({
      login: vi.fn(async () => {
        authState.isAuthenticated = true
        authState.accessToken = 'access-token'
        authState.idToken = 'id-token'
        authState.user = {
          id: 'user-2',
          cognito_sub: 'cognito-sub-2',
          name: 'Consultora Worton',
          email: 'consultora@example.com',
          role: 'consultant',
          created_at: '2026-04-06T00:00:00Z',
        }
      }),
    })

    mockUseAuth.mockImplementation(() => authState)

    renderApp('/login')

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'consultora@example.com' },
    })
    fireEvent.change(screen.getByLabelText(/senha/i), {
      target: { value: 'SenhaSegura123!' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: /entrar com segurança/i })
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /workspace liberado/i })
      ).toBeInTheDocument()
    })
  })
})
