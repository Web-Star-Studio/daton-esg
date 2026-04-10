import type { DocumentExtraction, ProjectDocument } from '../../types/project'

export type ExtractionDraft = {
  correction_reason: string
  corrected_esg_category: string
  corrected_period: string
  corrected_unit: string
  corrected_value: string
}

export type DrillDownView =
  | { level: 'categories' }
  | { level: 'documents'; category: string }
  | {
      level: 'extractions'
      category: string
      documentId: string
      documentName: string
    }

export const ESG_CATEGORY_OPTIONS = [
  'Visão e Estratégia',
  'Governança',
  'Ambiental',
  'Social',
  'Econômico',
  'Stakeholders',
  'Inovação',
  'Normas',
  'Comunicação',
  'Auditorias',
] as const

export const CATEGORY_ICONS: Record<string, string> = {
  'Visão e Estratégia': 'visibility',
  Governança: 'gavel',
  Ambiental: 'eco',
  Social: 'groups',
  Econômico: 'payments',
  Stakeholders: 'handshake',
  Inovação: 'lightbulb',
  Normas: 'policy',
  Comunicação: 'forum',
  Auditorias: 'fact_check',
  'Sem categoria': 'help_outline',
}

export function getConfidenceClasses(
  confidence: DocumentExtraction['confidence']
) {
  switch (confidence) {
    case 'high':
      return 'bg-[#e8f5e8] text-[#1a7a1a]'
    case 'low':
      return 'bg-[#fff8e8] text-[#9a6700]'
    case 'medium':
    default:
      return 'bg-[#f0f0f5] text-[#5c5c61]'
  }
}

export function getConfidenceLabel(
  confidence: DocumentExtraction['confidence']
) {
  switch (confidence) {
    case 'high':
      return 'Alta'
    case 'low':
      return 'Baixa'
    case 'medium':
    default:
      return 'Média'
  }
}

export function getReviewStatusLabel(
  status: DocumentExtraction['review_status']
) {
  switch (status) {
    case 'approved':
      return 'Aprovado'
    case 'corrected':
      return 'Corrigido'
    case 'ignored':
      return 'Ignorado'
    case 'pending':
    default:
      return 'Pendente'
  }
}

export function getReviewStatusClasses(
  status: DocumentExtraction['review_status']
) {
  switch (status) {
    case 'approved':
      return 'bg-[#eef6ff] text-[#0b73da]'
    case 'corrected':
      return 'bg-[#f6eefc] text-[#8b3fd1]'
    case 'ignored':
      return 'bg-[#f0f0f5] text-[#86868b]'
    case 'pending':
    default:
      return 'bg-[#fff8e8] text-[#9a6700]'
  }
}

export function getDocumentConfidenceLabel(
  confidence: ProjectDocument['classification_confidence']
) {
  switch (confidence) {
    case 'high':
      return 'Alta'
    case 'low':
      return 'Baixa'
    case 'medium':
      return 'Média'
    default:
      return 'Sem confiança'
  }
}

export function formatFileSize(fileSizeBytes: number | null) {
  if (!fileSizeBytes) {
    return 'Tamanho pendente'
  }

  if (fileSizeBytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(fileSizeBytes / 1024))} KB`
  }

  return `${(fileSizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

export function createDraft(extraction: DocumentExtraction): ExtractionDraft {
  return {
    correction_reason: extraction.correction_reason ?? '',
    corrected_esg_category:
      extraction.corrected_esg_category ??
      extraction.original_esg_category ??
      '',
    corrected_period:
      extraction.corrected_period ?? extraction.original_period ?? '',
    corrected_unit: extraction.corrected_unit ?? extraction.original_unit ?? '',
    corrected_value:
      extraction.corrected_value ?? extraction.original_value ?? '',
  }
}

export function buildCorrectionPayload(
  extraction: DocumentExtraction,
  draft: ExtractionDraft
) {
  const normCategory = draft.corrected_esg_category || null
  const normValue = draft.corrected_value || null
  const normUnit = draft.corrected_unit || null
  const normPeriod = draft.corrected_period || null

  const origCategory = extraction.original_esg_category ?? null
  const origValue = extraction.original_value ?? null
  const origUnit = extraction.original_unit ?? null
  const origPeriod = extraction.original_period ?? null

  const hasCategoryCorrection = normCategory !== origCategory
  const hasValueCorrection = normValue !== origValue
  const hasUnitCorrection = normUnit !== origUnit
  const hasPeriodCorrection = normPeriod !== origPeriod

  const hasCorrections =
    hasCategoryCorrection ||
    hasValueCorrection ||
    hasUnitCorrection ||
    hasPeriodCorrection

  return {
    corrected_esg_category: hasCategoryCorrection ? normCategory : null,
    corrected_period: hasPeriodCorrection ? normPeriod : null,
    corrected_unit: hasUnitCorrection ? normUnit : null,
    corrected_value: hasValueCorrection ? normValue : null,
    hasCorrections,
  }
}
