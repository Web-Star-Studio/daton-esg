export type DocumentDirectory = {
  key: string
  label: string
  order: number
  isLegacyOnly?: boolean
}

export const LEGACY_UNCATEGORIZED_DIRECTORY_KEY = 'sem-categoria'

export const DOCUMENT_DIRECTORIES: DocumentDirectory[] = [
  {
    key: 'a-empresa-sumario-executivo',
    label: '1. A Empresa (Sumário Executivo)',
    order: 1,
  },
  {
    key: 'visao-estrategica-de-sustentabilidade',
    label: '2. Visão Estratégica de Sustentabilidade',
    order: 2,
  },
  {
    key: 'governanca-corporativa',
    label: '3. Governança Corporativa',
    order: 3,
  },
  {
    key: 'gestao-ambiental',
    label: '4. Gestão Ambiental',
    order: 4,
  },
  {
    key: 'desempenho-social',
    label: '5. Desempenho Social',
    order: 5,
  },
  {
    key: 'gestao-de-desempenho-economico',
    label: '6. Gestão de Desempenho Econômico',
    order: 6,
  },
  {
    key: 'relacionamento-com-stakeholders',
    label: '7. Relacionamento com Stakeholders',
    order: 7,
  },
  {
    key: 'inovacao-e-desenvolvimento-tecnologico',
    label: '8. Inovação e Desenvolvimento Tecnológico',
    order: 8,
  },
  {
    key: 'relatorios-e-normas',
    label: '9. Relatórios e Normas',
    order: 9,
  },
  {
    key: 'comunicacao-e-transparencia',
    label: '10. Comunicação e Transparência',
    order: 10,
  },
  {
    key: 'auditorias-e-avaliacoes',
    label: '11. Auditorias e Avaliações',
    order: 11,
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
