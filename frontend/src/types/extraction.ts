export type ExtractionRunKind = 'materiality' | 'indicators' | 'both'

export type ExtractionRunStatus =
  | 'running'
  | 'completed'
  | 'failed'
  | 'partial'

export type ExtractionTargetKind =
  | 'material_topic'
  | 'sdg_goal'
  | 'indicator_value'

export type ExtractionConfidence = 'high' | 'medium' | 'low'

export type ExtractionSuggestionStatus =
  | 'pending'
  | 'accepted'
  | 'rejected'
  | 'edited'

export type ExtractionProvenance = {
  document_id: string
  document_name: string
  chunk_index: number
  excerpt: string
}

export type MaterialTopicSuggestionPayload = {
  pillar: 'E' | 'S'
  topic: string
  priority: 'alta' | 'media' | 'baixa'
  reasoning?: string
}

export type SdgSuggestionPayload = {
  ods_number: number
  objetivo: string
  acao: string
  indicador: string
  resultado: string
  reasoning?: string
}

export type IndicatorValueSuggestionPayload = {
  template_id: number
  tema: string
  indicador: string
  unidade: string
  value: string
  period?: string | null
  scope?: string | null
  reasoning?: string
}

export type ExtractionSuggestionPayload =
  | MaterialTopicSuggestionPayload
  | SdgSuggestionPayload
  | IndicatorValueSuggestionPayload

export type ExtractionRun = {
  id: string
  project_id: string
  kind: ExtractionRunKind
  status: ExtractionRunStatus
  triggered_by: string | null
  model_used: string | null
  documents_considered: string[] | null
  summary_stats: Record<string, unknown> | null
  error: string | null
  started_at: string
  completed_at: string | null
}

export type ExtractionSuggestion = {
  id: string
  run_id: string
  project_id: string
  target_kind: ExtractionTargetKind
  payload: ExtractionSuggestionPayload
  confidence: ExtractionConfidence
  confidence_score: number | null
  provenance: ExtractionProvenance[]
  conflict_with_existing: boolean
  existing_value_snapshot: Record<string, unknown> | null
  status: ExtractionSuggestionStatus
  reviewed_at: string | null
  reviewed_by: string | null
  reviewer_notes: string | null
  created_at: string
}

export type ExtractionSuggestionList = {
  items: ExtractionSuggestion[]
  total: number
}

export type ExtractionStreamEventType =
  | 'run_started'
  | 'extractor_started'
  | 'suggestion'
  | 'extractor_completed'
  | 'run_completed'
  | 'error'

export type ExtractionStreamEvent =
  | { type: 'run_started'; data: { run_id: string; kind: ExtractionRunKind; model: string | null } }
  | {
      type: 'extractor_started'
      data: { kind: 'materiality' | 'indicators' }
    }
  | { type: 'suggestion'; data: ExtractionSuggestion }
  | {
      type: 'extractor_completed'
      data: { kind: 'materiality' | 'indicators'; count: number }
    }
  | {
      type: 'run_completed'
      data: { run_id: string; status: ExtractionRunStatus; summary: Record<string, unknown> | null }
    }
  | { type: 'error'; data: { message: string; extractor?: string } }

export type UpdateExtractionSuggestionInput = {
  action: 'accept' | 'reject' | 'edit'
  payload?: ExtractionSuggestionPayload
  notes?: string
}

export type BulkExtractionSuggestionInput = {
  ids: string[]
  action: 'accept_all' | 'reject_all'
}

export type BulkExtractionSuggestionResponse = {
  succeeded: string[]
  failed: { id: string; detail: string }[]
}
