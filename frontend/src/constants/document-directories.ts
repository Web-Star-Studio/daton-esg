export type DocumentDirectory = {
  key: string
  label: string
  order: number
  isLegacyOnly?: boolean
}

export const LEGACY_UNCATEGORIZED_DIRECTORY_KEY = 'sem-categoria'

export const DOCUMENT_DIRECTORIES: DocumentDirectory[] = [
  {
    key: 'visao-estrategica-de-sustentabilidade',
    label: '1. Visão Estratégica de Sustentabilidade',
    order: 1,
  },
  {
    key: 'governanca-corporativa',
    label: '2. Governança Corporativa',
    order: 2,
  },
  {
    key: 'gestao-ambiental',
    label: '3. Gestão Ambiental',
    order: 3,
  },
  {
    key: 'desempenho-social',
    label: '4. Desempenho Social',
    order: 4,
  },
  {
    key: 'gestao-de-desempenho-economico',
    label: '5. Gestão de Desempenho Econômico',
    order: 5,
  },
  {
    key: 'relacionamento-com-stakeholders',
    label: '6. Relacionamento com Stakeholders',
    order: 6,
  },
  {
    key: 'inovacao-e-desenvolvimento-tecnologico',
    label: '7. Inovação e Desenvolvimento Tecnológico',
    order: 7,
  },
  {
    key: 'relatorios-e-normas',
    label: '8. Relatórios e Normas',
    order: 8,
  },
  {
    key: 'comunicacao-e-transparencia',
    label: '9. Comunicação e Transparência',
    order: 9,
  },
  {
    key: 'auditorias-e-avaliacoes',
    label: '10. Auditorias e Avaliações',
    order: 10,
  },
]

export const LEGACY_UNCATEGORIZED_DIRECTORY: DocumentDirectory = {
  key: LEGACY_UNCATEGORIZED_DIRECTORY_KEY,
  label: 'Sem categoria',
  order: 99,
  isLegacyOnly: true,
}

export const DOCUMENT_DIRECTORY_MAP = new Map(
  [...DOCUMENT_DIRECTORIES, LEGACY_UNCATEGORIZED_DIRECTORY].map((directory) => [
    directory.key,
    directory,
  ])
)

export function getDocumentDirectory(directoryKey: string) {
  return DOCUMENT_DIRECTORY_MAP.get(directoryKey) ?? null
}

export function isDocumentDirectoryKey(directoryKey: string) {
  return DOCUMENT_DIRECTORY_MAP.has(directoryKey)
}

export function getVisibleDocumentDirectories(
  hasLegacyUncategorizedDocuments: boolean
) {
  return hasLegacyUncategorizedDocuments
    ? [...DOCUMENT_DIRECTORIES, LEGACY_UNCATEGORIZED_DIRECTORY]
    : DOCUMENT_DIRECTORIES
}

export function getDocumentDirectoryLabel(directoryKey: string) {
  return getDocumentDirectory(directoryKey)?.label ?? null
}
