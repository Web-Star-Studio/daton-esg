import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useExtractionSuggestions } from '../hooks/use-extraction-suggestions'
import {
  bulkUpdateExtractionSuggestions,
  fetchExtractionRun,
  listExtractionSuggestions,
  startExtractionRun,
  streamExtractionRun,
  updateExtractionSuggestion,
  type ExtractionStreamHandlers,
} from '../services/api-client'
import type { ExtractionRun, ExtractionSuggestion } from '../types/extraction'

vi.mock('../services/api-client', () => ({
  bulkUpdateExtractionSuggestions: vi.fn(),
  fetchExtractionRun: vi.fn(),
  listExtractionSuggestions: vi.fn(),
  startExtractionRun: vi.fn(),
  streamExtractionRun: vi.fn(),
  updateExtractionSuggestion: vi.fn(),
}))

const mockList = vi.mocked(listExtractionSuggestions)
const mockStart = vi.mocked(startExtractionRun)
const mockStream = vi.mocked(streamExtractionRun)
const mockFetchRun = vi.mocked(fetchExtractionRun)
const mockUpdate = vi.mocked(updateExtractionSuggestion)
const mockBulk = vi.mocked(bulkUpdateExtractionSuggestions)

function makeSuggestion(
  id: string,
  overrides: Partial<ExtractionSuggestion> = {}
): ExtractionSuggestion {
  return {
    id,
    run_id: 'run-1',
    project_id: 'proj-1',
    target_kind: 'material_topic',
    payload: { pillar: 'E', topic: 'GRI 305-1', priority: 'alta' },
    confidence: 'high',
    confidence_score: null,
    provenance: [],
    conflict_with_existing: false,
    existing_value_snapshot: null,
    status: 'pending',
    reviewed_at: null,
    reviewed_by: null,
    reviewer_notes: null,
    created_at: '2026-04-17T00:00:00Z',
    ...overrides,
  }
}

const fakeRun: ExtractionRun = {
  id: 'run-1',
  project_id: 'proj-1',
  kind: 'materiality',
  status: 'running',
  triggered_by: null,
  model_used: null,
  documents_considered: null,
  summary_stats: null,
  error: null,
  started_at: '2026-04-17T00:00:00Z',
  completed_at: null,
}

describe('useExtractionSuggestions', () => {
  beforeEach(() => {
    mockList.mockReset()
    mockStart.mockReset()
    mockStream.mockReset()
    mockFetchRun.mockReset()
    mockUpdate.mockReset()
    mockBulk.mockReset()

    mockList.mockResolvedValue({ items: [], total: 0 })
  })

  it('loads pending suggestions on mount', async () => {
    mockList.mockResolvedValue({
      items: [makeSuggestion('s1')],
      total: 1,
    })
    const { result } = renderHook(() =>
      useExtractionSuggestions('proj-1', { targetKind: 'material_topic' })
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    expect(result.current.suggestions).toHaveLength(1)
    expect(result.current.suggestions[0].id).toBe('s1')
    expect(mockList).toHaveBeenCalledWith('proj-1', {
      status: 'pending',
      limit: 500,
    })
  })

  it('does not load when projectId is null', async () => {
    renderHook(() => useExtractionSuggestions(null))
    // Give microtasks a chance — list should never be called.
    await new Promise((r) => setTimeout(r, 10))
    expect(mockList).not.toHaveBeenCalled()
  })

  it('filters incoming suggestions by targetKind array', async () => {
    const sMaterial = makeSuggestion('m1', { target_kind: 'material_topic' })
    const sIndicator = makeSuggestion('i1', {
      target_kind: 'indicator_value',
    })
    mockList.mockResolvedValue({
      items: [sMaterial, sIndicator],
      total: 2,
    })

    const { result } = renderHook(() =>
      useExtractionSuggestions('proj-1', {
        targetKind: ['material_topic', 'sdg_goal'],
      })
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    expect(result.current.suggestions.map((s) => s.id)).toEqual(['m1'])
  })

  it('startRun appends streamed suggestions and refreshes run on completion', async () => {
    mockList.mockResolvedValue({ items: [], total: 0 })
    mockStart.mockResolvedValue(fakeRun)

    const completedRun: ExtractionRun = { ...fakeRun, status: 'completed' }
    mockFetchRun.mockResolvedValue(completedRun)

    let capturedHandlers: ExtractionStreamHandlers | null = null
    mockStream.mockImplementation(async (_pid, _rid, handlers) => {
      capturedHandlers = handlers
    })

    const { result } = renderHook(() =>
      useExtractionSuggestions('proj-1', { targetKind: 'material_topic' })
    )
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    await act(async () => {
      await result.current.startRun('materiality')
    })

    expect(mockStart).toHaveBeenCalledWith('proj-1', 'materiality')
    expect(capturedHandlers).not.toBeNull()

    await act(async () => {
      capturedHandlers!.onSuggestion?.(makeSuggestion('s-new'))
    })
    expect(result.current.suggestions.map((s) => s.id)).toContain('s-new')

    await act(async () => {
      await capturedHandlers!.onCompleted?.({
        run_id: 'run-1',
        status: 'completed',
        summary: null,
      })
    })
    expect(result.current.run?.status).toBe('completed')
    expect(result.current.isStreaming).toBe(false)
  })

  it('streamed suggestions of the wrong target_kind are ignored', async () => {
    mockStart.mockResolvedValue(fakeRun)
    let capturedHandlers: ExtractionStreamHandlers | null = null
    mockStream.mockImplementation(async (_p, _r, handlers) => {
      capturedHandlers = handlers
    })

    const { result } = renderHook(() =>
      useExtractionSuggestions('proj-1', { targetKind: 'indicator_value' })
    )
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    await act(async () => {
      await result.current.startRun('indicators')
    })
    await act(async () => {
      capturedHandlers!.onSuggestion?.(
        makeSuggestion('m1', { target_kind: 'material_topic' })
      )
    })
    expect(result.current.suggestions).toHaveLength(0)
  })

  it('updateSuggestion(accept) removes the item from local list on success', async () => {
    mockList.mockResolvedValue({
      items: [makeSuggestion('s1'), makeSuggestion('s2')],
      total: 2,
    })
    mockUpdate.mockResolvedValue(makeSuggestion('s1', { status: 'accepted' }))

    const { result } = renderHook(() =>
      useExtractionSuggestions('proj-1', { targetKind: 'material_topic' })
    )
    await waitFor(() => expect(result.current.suggestions).toHaveLength(2))

    await act(async () => {
      await result.current.updateSuggestion('s1', { action: 'accept' })
    })
    expect(mockUpdate).toHaveBeenCalledWith('proj-1', 's1', {
      action: 'accept',
    })
    expect(result.current.suggestions.map((s) => s.id)).toEqual(['s2'])
  })

  it('bulkUpdate filters succeeded ids out of local list', async () => {
    mockList.mockResolvedValue({
      items: [makeSuggestion('s1'), makeSuggestion('s2'), makeSuggestion('s3')],
      total: 3,
    })
    mockBulk.mockResolvedValue({ succeeded: ['s1', 's3'], failed: [] })

    const { result } = renderHook(() =>
      useExtractionSuggestions('proj-1', { targetKind: 'material_topic' })
    )
    await waitFor(() => expect(result.current.suggestions).toHaveLength(3))

    await act(async () => {
      await result.current.bulkUpdate({
        ids: ['s1', 's3'],
        action: 'accept_all',
      })
    })
    expect(result.current.suggestions.map((s) => s.id)).toEqual(['s2'])
  })
})
