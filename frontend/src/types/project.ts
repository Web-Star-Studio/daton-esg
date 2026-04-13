export type ProjectRecord = {
  id: string
  org_name: string
  org_sector: string | null
  org_size: string | null
  org_location: string | null
  base_year: number
  scope: string | null
  status: string
  material_topics: Record<string, unknown> | Array<unknown> | null
  sdg_goals: Record<string, unknown> | Array<unknown> | null
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
  material_topics?: Record<string, unknown> | Array<unknown> | null
  sdg_goals?: Record<string, unknown> | Array<unknown> | null
  status?: string
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
