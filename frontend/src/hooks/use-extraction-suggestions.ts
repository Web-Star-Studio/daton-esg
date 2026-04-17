import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  bulkUpdateExtractionSuggestions,
  fetchExtractionRun,
  listExtractionSuggestions,
  startExtractionRun,
  streamExtractionRun,
  updateExtractionSuggestion,
  type ExtractionStreamHandlers,
} from '../services/api-client'
import type {
  BulkExtractionSuggestionInput,
  ExtractionRun,
  ExtractionRunKind,
  ExtractionSuggestion,
  ExtractionTargetKind,
  UpdateExtractionSuggestionInput,
} from '../types/extraction'

type State = {
  run: ExtractionRun | null
  suggestions: ExtractionSuggestion[]
  isLoading: boolean
  isStreaming: boolean
  error: string | null
}

type Options = {
  /** Restrict the panel to suggestions for this target_kind. When omitted,
   * the panel shows everything (used by a "global" entry point if needed). */
  targetKind?: ExtractionTargetKind | ExtractionTargetKind[]
}

function matchesTarget(
  suggestion: ExtractionSuggestion,
  filter: Options['targetKind']
) {
  if (!filter) return true
  const list = Array.isArray(filter) ? filter : [filter]
  return list.includes(suggestion.target_kind)
}

export function useExtractionSuggestions(
  projectId: string | null,
  options: Options = {}
) {
  const { targetKind } = options
  // Stable key derived from the filter so consumers can pass an inline array
  // literal without triggering a re-render loop. The actual filter value is
  // kept in a ref so callbacks can read the latest value without having to
  // depend on it.
  const targetKindKey = Array.isArray(targetKind)
    ? targetKind.slice().sort().join('|')
    : (targetKind ?? '')
  const targetKindRef = useRef<Options['targetKind']>(targetKind)
  targetKindRef.current = targetKind

  const [state, setState] = useState<State>({
    run: null,
    suggestions: [],
    isLoading: false,
    isStreaming: false,
    error: null,
  })
  const abortRef = useRef<AbortController | null>(null)

  const loadPending = useCallback(async () => {
    if (!projectId) return
    setState((prev) => ({ ...prev, isLoading: true, error: null }))
    try {
      const result = await listExtractionSuggestions(projectId, {
        status: 'pending',
        limit: 500,
      })
      const filtered = result.items.filter((item) =>
        matchesTarget(item, targetKindRef.current)
      )
      setState((prev) => ({
        ...prev,
        suggestions: filtered,
        isLoading: false,
      }))
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : String(err),
      }))
    }
  }, [projectId, targetKindKey])

  useEffect(() => {
    void loadPending()
  }, [loadPending])

  const startRun = useCallback(
    async (kind: ExtractionRunKind) => {
      if (!projectId) return
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setState((prev) => ({
        ...prev,
        isStreaming: true,
        error: null,
      }))

      try {
        const run = await startExtractionRun(projectId, kind)
        setState((prev) => ({ ...prev, run }))

        const handlers: ExtractionStreamHandlers = {
          onSuggestion: (suggestion) => {
            if (!matchesTarget(suggestion, targetKindRef.current)) return
            setState((prev) => {
              if (prev.suggestions.some((s) => s.id === suggestion.id))
                return prev
              return {
                ...prev,
                suggestions: [suggestion, ...prev.suggestions],
              }
            })
          },
          onCompleted: async () => {
            try {
              const refreshed = await fetchExtractionRun(projectId, run.id)
              setState((prev) => ({
                ...prev,
                run: refreshed,
                isStreaming: false,
              }))
            } catch {
              setState((prev) => ({ ...prev, isStreaming: false }))
            }
          },
          onError: (message) => {
            setState((prev) => ({ ...prev, error: message }))
          },
        }

        await streamExtractionRun(projectId, run.id, handlers, {
          signal: controller.signal,
        })
      } catch (err) {
        if (controller.signal.aborted) return
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: err instanceof Error ? err.message : String(err),
        }))
      }
    },
    [projectId]
  )

  const updateSuggestion = useCallback(
    async (
      suggestionId: string,
      payload: UpdateExtractionSuggestionInput
    ): Promise<ExtractionSuggestion | null> => {
      if (!projectId) return null
      try {
        const updated = await updateExtractionSuggestion(
          projectId,
          suggestionId,
          payload
        )
        setState((prev) => ({
          ...prev,
          suggestions: prev.suggestions.filter((s) => s.id !== suggestionId),
        }))
        return updated
      } catch (err) {
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : String(err),
        }))
        return null
      }
    },
    [projectId]
  )

  const bulkUpdate = useCallback(
    async (payload: BulkExtractionSuggestionInput) => {
      if (!projectId) return null
      try {
        const result = await bulkUpdateExtractionSuggestions(projectId, payload)
        const succeededIds = new Set(result.succeeded)
        setState((prev) => ({
          ...prev,
          suggestions: prev.suggestions.filter(
            (s) => !succeededIds.has(s.id)
          ),
        }))
        return result
      } catch (err) {
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : String(err),
        }))
        return null
      }
    },
    [projectId]
  )

  const refresh = loadPending

  const stopStream = useCallback(() => {
    abortRef.current?.abort()
    setState((prev) => ({ ...prev, isStreaming: false }))
  }, [])

  useEffect(() => () => abortRef.current?.abort(), [])

  return useMemo(
    () => ({
      run: state.run,
      suggestions: state.suggestions,
      isLoading: state.isLoading,
      isStreaming: state.isStreaming,
      error: state.error,
      startRun,
      updateSuggestion,
      bulkUpdate,
      refresh,
      stopStream,
    }),
    [
      state.run,
      state.suggestions,
      state.isLoading,
      state.isStreaming,
      state.error,
      startRun,
      updateSuggestion,
      bulkUpdate,
      refresh,
      stopStream,
    ]
  )
}
