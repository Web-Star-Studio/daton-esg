export type MaterialTopicPillar = 'E' | 'S' | 'G'

export type MaterialTopic = {
  pillar: MaterialTopicPillar
  topic: string
  priority: number
}

export type SdgSelection = {
  ods_number: number
  objetivo: string
  acao: string
  indicador: string
  resultado: string
}

export type IndicatorValue = {
  tema: string
  indicador: string
  unidade: string
  value: string
}

export type ProjectRecord = {
  id: string
  org_name: string
  org_sector: string | null
  org_size: string | null
  org_location: string | null
  base_year: number
  scope: string | null
  status: string
  material_topics: MaterialTopic[] | Record<string, unknown> | null
  sdg_goals: SdgSelection[] | Record<string, unknown> | null
  indicator_values: IndicatorValue[] | null
  created_at: string
  updated_at: string
}

export type ProjectCreateInput = {
  org_name: string
  org_sector: string | null
  org_size: string | null
  org_location: string | null
  base_year: number
  scope: string | null
}

export type ProjectUpdateInput = Partial<ProjectCreateInput> & {
  material_topics?: MaterialTopic[] | null
  sdg_goals?: SdgSelection[] | null
  indicator_values?: IndicatorValue[] | null
  status?: string
}

export type GriStandardRecord = {
  code: string
  family: string
  standard_text: string
}

export type OdsMetaRecord = {
  meta_code: string
  meta_text: string
}

export type OdsGoalRecord = {
  ods_number: number
  objetivo: string
  metas: OdsMetaRecord[]
}

export type IndicatorTemplateRecord = {
  tema: string
  indicador: string
  unidade: string
}

export type ReportStatus =
  | 'generating'
  | 'failed'
  | 'draft'
  | 'reviewed'
  | 'exported'

export type ReportSectionAudit = {
  agent_name: string
  section_key: string
  system_prompt_hash: string
  system_prompt_length: number
  user_prompt_length: number
  rag_chunks_received: Array<{
    filename: string
    directory_key: string
    score: number
  }>
  reference_chunks_received: Array<{ code: string | null; score: number }>
  gri_codes_assigned: string[]
  gri_codes_produced: string[]
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  latency_ms: number
  model_id: string
  temperature: number
  started_at: string
  completed_at: string
}

export type ReportSection = {
  key: string
  title: string
  order: number
  heading_level: number
  content: string
  gri_codes_used: string[]
  word_count: number
  status: 'completed' | 'sparse_data' | 'failed'
  audit?: ReportSectionAudit | null
}

export type GriIndexEntry = {
  code: string
  family: string
  standard_text: string
  evidence_excerpt: string | null
  section_ref: string | null
  status: 'atendido' | 'parcial' | 'nao_atendido'
  found_in_text: boolean
}

export type ReportGapGroup =
  | 'vocabulary_warning'
  | 'content_gap'
  | 'generation_issue'

export type ReportGapCategory =
  | 'forbidden_term'
  | 'sparse_evidence'
  | 'missing_enquadramento'
  | 'missing_gri_code'
  | 'controlled_term_flag'
  | 'generation_error'
  | 'inline_gap_warning'

export type ReportGapSeverity = 'info' | 'warning' | 'critical'
export type ReportGapPriority = 'low' | 'medium' | 'high'

export type ReportGap = {
  section_key: string | null
  group?: ReportGapGroup | null
  category: ReportGapCategory
  detail: string
  title?: string | null
  recommendation?: string | null
  severity?: ReportGapSeverity | null
  priority?: ReportGapPriority | null
  missing_data_type?: string | null
  suggested_document?: string | null
  related_gri_codes?: string[] | null
}

export type ReportListItem = {
  id: string
  project_id: string
  version: number
  status: ReportStatus
  created_at: string
  updated_at: string
}

export type ReportRecord = {
  id: string
  project_id: string
  version: number
  status: ReportStatus
  sections: ReportSection[] | null
  gri_index: GriIndexEntry[] | null
  gaps: ReportGap[] | null
  indicators: unknown
  charts: unknown
  exported_docx_s3: string | null
  exported_pdf_s3: string | null
  llm_tokens_used: number | null
  created_at: string
  updated_at: string
}

export type ProjectShellOption = {
  id: string
  href: string
  name: string
}

export type ProjectDocument = {
  id: string
  project_id: string
  filename: string
  file_type: 'pdf' | 'xlsx' | 'csv' | 'docx'
  s3_key: string
  directory_key: string
  file_size_bytes: number | null
  indexing_status: 'pending' | 'processing' | 'indexed' | 'failed'
  indexing_error: string | null
  indexed_at: string | null
  created_at: string
}

export type CreateProjectDocumentUploadInput = {
  filename: string
  file_size_bytes: number
  directory_key: string
}

export type ProjectDocumentUploadSession = {
  document_id: string
  upload_url: string
  s3_key: string
  content_type: string
  expires_in_seconds: number
}

export type MoveProjectDocumentInput = {
  directory_key: string
}

export type ProjectKnowledgeStatus = {
  total_documents: number
  pending_documents: number
  processing_documents: number
  indexed_documents: number
  failed_documents: number
  total_chunks: number
  last_indexed_at: string | null
}

export type ProjectKnowledgeReindexResponse = {
  project_id: string
  queued_documents: number
}

export type ProjectGenerationCitation = {
  document_id: string | null
  filename: string
  directory_key: string | null
  chunk_index: number
  source_type: string
  score: number
  snippet: string
}

export type ProjectGenerationMessage = {
  id: string
  thread_id: string
  project_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations: ProjectGenerationCitation[]
  created_at: string
}

export type ProjectGenerationThread = {
  id: string
  project_id: string
  title: string
  created_at: string
  updated_at: string
}

export type ProjectGenerationThreadDetail = {
  thread: ProjectGenerationThread
  messages: ProjectGenerationMessage[]
}
