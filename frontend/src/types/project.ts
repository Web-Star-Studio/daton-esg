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
  file_size_bytes: number | null
  parsing_status: 'pending' | 'processing' | 'completed' | 'failed'
  extracted_text: string | null
  parsed_payload: Record<string, unknown> | null
  parsing_error: string | null
  esg_category: string | null
  classification_confidence: 'high' | 'medium' | 'low' | null
  created_at: string
}

export type DocumentExtraction = {
  id: string
  project_id: string
  document_id: string
  document_filename: string | null
  source_kind: 'paragraph' | 'table_row' | 'table_cell' | 'sheet_row'
  source_locator: Record<string, unknown> | null
  source_snippet: string
  label: string | null
  original_value: string | null
  original_unit: string | null
  original_period: string | null
  original_esg_category: string | null
  corrected_value: string | null
  corrected_unit: string | null
  corrected_period: string | null
  corrected_esg_category: string | null
  effective_value: string | null
  effective_unit: string | null
  effective_period: string | null
  effective_esg_category: string | null
  confidence: 'high' | 'medium' | 'low' | null
  review_status: 'pending' | 'approved' | 'corrected' | 'ignored'
  correction_reason: string | null
  reviewed_by_user_id: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export type CreateProjectDocumentUploadInput = {
  filename: string
  file_size_bytes: number
}

export type ProjectDocumentUploadSession = {
  document_id: string
  upload_url: string
  s3_key: string
  content_type: string
  expires_in_seconds: number
}

export type UpdateDocumentExtractionInput = {
  corrected_value?: string | null
  corrected_unit?: string | null
  corrected_period?: string | null
  corrected_esg_category?: string | null
  review_status: 'pending' | 'approved' | 'corrected' | 'ignored'
  correction_reason?: string | null
}
