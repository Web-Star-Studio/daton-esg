import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ExtractionSuggestionsPanel } from '../components/extraction-suggestions-panel'
import type { ExtractionSuggestion } from '../types/extraction'

const materialitySuggestion: ExtractionSuggestion = {
  id: 'sug-1',
  run_id: 'run-1',
  project_id: 'proj-1',
  target_kind: 'material_topic',
  payload: { pillar: 'E', topic: 'GRI 305-1', priority: 'alta' },
  confidence: 'high',
  confidence_score: null,
  provenance: [
    {
      document_id: 'doc-1',
      document_name: 'relatorio-2024.pdf',
      chunk_index: 7,
      excerpt: 'A organização emitiu 15.000 tCO2e em 2024.',
    },
  ],
  conflict_with_existing: false,
  existing_value_snapshot: null,
  status: 'pending',
  reviewed_at: null,
  reviewed_by: null,
  reviewer_notes: null,
  created_at: '2026-04-17T00:00:00Z',
}

const indicatorSuggestion: ExtractionSuggestion = {
  id: 'sug-2',
  run_id: 'run-1',
  project_id: 'proj-1',
  target_kind: 'indicator_value',
  payload: {
    template_id: 42,
    tema: 'Clima e Energia',
    indicador: 'Energia consumida — renovável',
    unidade: 'kWh/ano',
    value: '1234.5',
  },
  confidence: 'medium',
  confidence_score: null,
  provenance: [
    {
      document_id: 'doc-2',
      document_name: 'energia-2024.xlsx',
      chunk_index: 1,
      excerpt: 'Renovável: 1.234,5 kWh',
    },
  ],
  conflict_with_existing: true,
  existing_value_snapshot: {
    tema: 'Clima e Energia',
    indicador: 'Energia consumida — renovável',
    unidade: 'kWh/ano',
    value: '0',
  },
  status: 'pending',
  reviewed_at: null,
  reviewed_by: null,
  reviewer_notes: 'unidade divergente: sugerido kWh, esperado kWh/ano',
  created_at: '2026-04-17T00:01:00Z',
}

function defaultProps() {
  return {
    isOpen: true,
    onClose: vi.fn(),
    title: 'Sugestões',
    suggestions: [materialitySuggestion, indicatorSuggestion],
    isStreaming: false,
    isLoading: false,
    error: null as string | null,
    onAccept: vi.fn(async () => {}),
    onReject: vi.fn(async () => {}),
    onAcceptAll: vi.fn(async () => {}),
    onRejectAll: vi.fn(async () => {}),
    onStart: vi.fn(),
  }
}

describe('ExtractionSuggestionsPanel', () => {
  it('renders pending suggestions with confidence badge', () => {
    render(<ExtractionSuggestionsPanel {...defaultProps()} />)
    expect(
      screen.getByText(/2 sugestão\(ões\) para revisar/)
    ).toBeInTheDocument()
    expect(screen.getByText('[E] GRI 305-1')).toBeInTheDocument()
    expect(
      screen.getByText('Energia consumida — renovável')
    ).toBeInTheDocument()
    expect(screen.getAllByText(/Alta|Média/).length).toBeGreaterThan(0)
  })

  it('shows the start button and triggers onStart on click', () => {
    const props = defaultProps()
    render(<ExtractionSuggestionsPanel {...props} />)
    const button = screen.getByTestId('extraction-start')
    fireEvent.click(button)
    expect(props.onStart).toHaveBeenCalledTimes(1)
  })

  it('renders conflict banner with existing snapshot when conflict_with_existing is true', () => {
    render(<ExtractionSuggestionsPanel {...defaultProps()} />)
    expect(
      screen.getByText('Conflito com valor já preenchido')
    ).toBeInTheDocument()
    expect(
      screen.getByText(/unidade divergente: sugerido kWh, esperado kWh\/ano/i)
    ).toBeInTheDocument()
    // The conflict suggestion uses 'Substituir' instead of 'Aceitar'
    expect(
      screen.getByRole('button', { name: 'Substituir' })
    ).toBeInTheDocument()
  })

  it('calls onAccept and onReject when buttons are clicked', () => {
    const props = defaultProps()
    render(<ExtractionSuggestionsPanel {...props} />)
    const acceptButtons = screen.getAllByRole('button', {
      name: /Aceitar$|Substituir/,
    })
    fireEvent.click(acceptButtons[0])
    expect(props.onAccept).toHaveBeenCalledWith(materialitySuggestion)

    const rejectButtons = screen.getAllByRole('button', { name: 'Rejeitar' })
    fireEvent.click(rejectButtons[0])
    expect(props.onReject).toHaveBeenCalledWith(materialitySuggestion)
  })

  it('renders empty state when no suggestions', () => {
    render(
      <ExtractionSuggestionsPanel
        {...defaultProps()}
        suggestions={[]}
        emptyHint="Nada por enquanto."
      />
    )
    expect(screen.getByText('Nada por enquanto.')).toBeInTheDocument()
    expect(screen.queryByText(/Aceitar todas/)).not.toBeInTheDocument()
  })

  it('shows streaming label when isStreaming is true', () => {
    render(
      <ExtractionSuggestionsPanel
        {...defaultProps()}
        suggestions={[]}
        isStreaming={true}
      />
    )
    expect(screen.getByText('Extraindo dos documentos…')).toBeInTheDocument()
    expect(screen.getByTestId('extraction-start')).toBeDisabled()
  })
})
