from __future__ import annotations

from dataclasses import dataclass

LEGACY_UNCATEGORIZED_DIRECTORY_KEY = "sem-categoria"


@dataclass(frozen=True, slots=True)
class DocumentDirectory:
    key: str
    label: str
    order: int


DOCUMENT_DIRECTORIES: tuple[DocumentDirectory, ...] = (
    DocumentDirectory(
        key="visao-estrategica-de-sustentabilidade",
        label="1. Visão Estratégica de Sustentabilidade",
        order=1,
    ),
    DocumentDirectory(
        key="governanca-corporativa",
        label="2. Governança Corporativa",
        order=2,
    ),
    DocumentDirectory(
        key="gestao-ambiental",
        label="3. Gestão Ambiental",
        order=3,
    ),
    DocumentDirectory(
        key="desempenho-social",
        label="4. Desempenho Social",
        order=4,
    ),
    DocumentDirectory(
        key="gestao-de-desempenho-economico",
        label="5. Gestão de Desempenho Econômico",
        order=5,
    ),
    DocumentDirectory(
        key="relacionamento-com-stakeholders",
        label="6. Relacionamento com Stakeholders",
        order=6,
    ),
    DocumentDirectory(
        key="inovacao-e-desenvolvimento-tecnologico",
        label="7. Inovação e Desenvolvimento Tecnológico",
        order=7,
    ),
    DocumentDirectory(
        key="relatorios-e-normas",
        label="8. Relatórios e Normas",
        order=8,
    ),
    DocumentDirectory(
        key="comunicacao-e-transparencia",
        label="9. Comunicação e Transparência",
        order=9,
    ),
    DocumentDirectory(
        key="auditorias-e-avaliacoes",
        label="10. Auditorias e Avaliações",
        order=10,
    ),
)

LEGACY_UNCATEGORIZED_DIRECTORY = DocumentDirectory(
    key=LEGACY_UNCATEGORIZED_DIRECTORY_KEY,
    label="Sem categoria",
    order=99,
)

DOCUMENT_DIRECTORY_BY_KEY = {
    directory.key: directory
    for directory in (*DOCUMENT_DIRECTORIES, LEGACY_UNCATEGORIZED_DIRECTORY)
}

LEGACY_ESG_CATEGORY_TO_DIRECTORY_KEY = {
    "Visão e Estratégia": "visao-estrategica-de-sustentabilidade",
    "Governança": "governanca-corporativa",
    "Ambiental": "gestao-ambiental",
    "Social": "desempenho-social",
    "Econômico": "gestao-de-desempenho-economico",
    "Stakeholders": "relacionamento-com-stakeholders",
    "Inovação": "inovacao-e-desenvolvimento-tecnologico",
    "Normas": "relatorios-e-normas",
    "Comunicação": "comunicacao-e-transparencia",
    "Auditorias": "auditorias-e-avaliacoes",
}


def is_valid_directory_key(directory_key: str) -> bool:
    return directory_key in DOCUMENT_DIRECTORY_BY_KEY


def is_official_directory_key(directory_key: str) -> bool:
    return any(directory.key == directory_key for directory in DOCUMENT_DIRECTORIES)


def get_directory_label(directory_key: str) -> str | None:
    directory = DOCUMENT_DIRECTORY_BY_KEY.get(directory_key)
    return directory.label if directory else None
