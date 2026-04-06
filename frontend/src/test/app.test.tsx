import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import App from '../App'

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
  })

  it('renders the initial placeholder route', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    )

    expect(screen.getByText(/worton esg report generator/i)).toBeInTheDocument()
    expect(
      screen.getByText(/base inicial do frontend para operar projetos/i)
    ).toBeInTheDocument()
  })
})
