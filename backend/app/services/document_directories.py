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
        key="a-empresa-sumario-executivo",
        label="1. A Empresa (Sumário Executivo)",
        order=1,
    ),
    DocumentDirectory(
        key="visao-estrategica-de-sustentabilidade",
        label="2. Visão Estratégica de Sustentabilidade",
        order=2,
    ),
    DocumentDirectory(
        key="governanca-corporativa",
        label="3. Governança Corporativa",
        order=3,
    ),
    DocumentDirectory(
        key="gestao-ambiental",
        label="4. Gestão Ambiental",
        order=4,
    ),
    DocumentDirectory(
        key="desempenho-social",
        label="5. Desempenho Social",
        order=5,
    ),
    DocumentDirectory(
        key="gestao-de-desempenho-economico",
        label="6. Gestão de Desempenho Econômico",
        order=6,
    ),
    DocumentDirectory(
        key="relacionamento-com-stakeholders",
        label="7. Relacionamento com Stakeholders",
        order=7,
    ),
    DocumentDirectory(
        key="inovacao-e-desenvolvimento-tecnologico",
        label="8. Inovação e Desenvolvimento Tecnológico",
        order=8,
    ),
    DocumentDirectory(
        key="relatorios-e-normas",
        label="9. Relatórios e Normas",
        order=9,
    ),
    DocumentDirectory(
        key="comunicacao-e-transparencia",
        label="10. Comunicação e Transparência",
        order=10,
    ),
    DocumentDirectory(
        key="auditorias-e-avaliacoes",
        label="11. Auditorias e Avaliações",
        order=11,
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
