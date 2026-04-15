"""Section manifest for the ESG preliminary report.

The manifest is static Python — it's the drafting pipeline's contract for the
shape of the output. Each section template declares:
  - key / title / order
  - heading_level (1 for top-level major sections; 2 for subsections later)
  - directory_keys — which document directories should be queried in RAG for
    this section's project evidence (matches keys in
    ``app.services.document_directories.DOCUMENT_DIRECTORIES``)
  - gri_codes — the actionable GRI codes this section is expected to cover
    (inline ``(GRI X-Y)`` parentheticals will draw from this subset)
  - rag_queries — 2–3 semantic queries per section for good coverage
  - target_words — rough budget for prompt + post-check enforcement
  - prompt_strategy — selects prompt template in the LangGraph generator

Structure reflects the Cooperlíquidos preliminary report shape, adjusted for
feasibility at MVP scale. Minor sub-structure (multi-level org, per-facility
tables) surfaces inside narrative rather than as separate templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PromptStrategy = Literal[
    "narrative",
    "narrative_with_table",
    "indicator_driven",
    "materialidade",
    "plano_acao",
    "gri_summary",
    "ods_alignment",
]


@dataclass(frozen=True, slots=True)
class ReportSectionTemplate:
    key: str
    title: str
    order: int
    heading_level: int
    directory_keys: tuple[str, ...]
    gri_codes: tuple[str, ...]
    rag_queries: tuple[str, ...]
    target_words: int
    prompt_strategy: PromptStrategy


REPORT_SECTIONS: tuple[ReportSectionTemplate, ...] = (
    ReportSectionTemplate(
        key="a-empresa",
        title="A Empresa",
        order=1,
        heading_level=1,
        directory_keys=("a-empresa-sumario-executivo",),
        gri_codes=("GRI 2-1", "GRI 2-2", "GRI 2-6"),
        rag_queries=(
            "sumario executivo institucional perfil organizacional identidade natureza juridica fundacao cnpj sede",
            "principais atividades produtos servicos mercados atendidos unidades abrangencia geografica porte operacional",
            "entidades incluidas no relato estrutura societaria escopo organizacional cadeia de valor fornecedores clientes",
        ),
        target_words=1200,
        prompt_strategy="narrative",
    ),
    ReportSectionTemplate(
        key="visao-estrategia",
        title="Visão e Estratégia de Sustentabilidade",
        order=2,
        heading_level=1,
        directory_keys=("visao-estrategica-de-sustentabilidade",),
        gri_codes=("GRI 2-22", "GRI 2-23", "GRI 2-24", "GRI 2-26"),
        rag_queries=(
            "estrategia de sustentabilidade compromissos publicos",
            "metas ambientais sociais e economicas de longo prazo",
            "politica institucional de sustentabilidade",
        ),
        target_words=1800,
        prompt_strategy="narrative",
    ),
    ReportSectionTemplate(
        key="governanca",
        title="Governança Corporativa",
        order=3,
        heading_level=1,
        directory_keys=("governanca-corporativa",),
        gri_codes=(
            "GRI 2-9",
            "GRI 2-10",
            "GRI 2-11",
            "GRI 2-12",
            "GRI 2-13",
            "GRI 2-15",
            "GRI 2-26",
            "GRI 2-27",
        ),
        rag_queries=(
            "estrutura de governanca organograma conselho",
            "codigo de etica compliance anticorrupcao",
            "gestao de riscos e conformidade",
        ),
        target_words=2400,
        prompt_strategy="narrative",
    ),
    ReportSectionTemplate(
        key="gestao-ambiental",
        title="Gestão Ambiental",
        order=4,
        heading_level=1,
        directory_keys=("gestao-ambiental",),
        gri_codes=(
            "GRI 302-1",
            "GRI 302-3",
            "GRI 303-3",
            "GRI 303-5",
            "GRI 305-1",
            "GRI 305-2",
            "GRI 305-3",
            "GRI 306-3",
        ),
        rag_queries=(
            "consumo de energia e emissoes GEE escopo 1 2 3",
            "consumo de agua efluentes e reuso",
            "residuos solidos destinacao e reciclagem",
            "licenciamento ambiental certificacoes ISO 14001",
        ),
        target_words=3500,
        prompt_strategy="indicator_driven",
    ),
    ReportSectionTemplate(
        key="desempenho-social",
        title="Desempenho Social",
        order=5,
        heading_level=1,
        directory_keys=("desempenho-social",),
        gri_codes=(
            "GRI 401-1",
            "GRI 403-1",
            "GRI 403-9",
            "GRI 404-1",
            "GRI 405-1",
            "GRI 413-1",
        ),
        rag_queries=(
            "saude e seguranca ocupacional taxa de acidentes",
            "diversidade e inclusao por nivel hierarquico",
            "treinamento e desenvolvimento de colaboradores",
            "projetos sociais e investimentos comunitarios",
        ),
        target_words=3000,
        prompt_strategy="indicator_driven",
    ),
    ReportSectionTemplate(
        key="desempenho-economico",
        title="Gestão e Desempenho Econômico",
        order=6,
        heading_level=1,
        directory_keys=("gestao-de-desempenho-economico",),
        gri_codes=(
            "GRI 201-1",
            "GRI 203-1",
            "GRI 204-1",
        ),
        rag_queries=(
            "desempenho economico receita valor distribuido",
            "investimentos em sustentabilidade CAPEX OPEX",
            "politica de compras sustentaveis e fornecedores",
        ),
        target_words=1800,
        prompt_strategy="indicator_driven",
    ),
    ReportSectionTemplate(
        key="stakeholders",
        title="Relacionamento com Stakeholders",
        order=7,
        heading_level=1,
        directory_keys=("relacionamento-com-stakeholders",),
        gri_codes=("GRI 2-29", "GRI 413-1"),
        rag_queries=(
            "matriz de stakeholders e priorizacao",
            "engajamento consulta e pesquisa de satisfacao",
            "parcerias institucionais associacoes setoriais",
        ),
        target_words=1600,
        prompt_strategy="narrative",
    ),
    ReportSectionTemplate(
        key="inovacao",
        title="Inovação e Desenvolvimento Tecnológico",
        order=8,
        heading_level=1,
        directory_keys=("inovacao-e-desenvolvimento-tecnologico",),
        gri_codes=("GRI 203-1", "GRI 302-4"),
        rag_queries=(
            "projetos de pesquisa e desenvolvimento em sustentabilidade",
            "tecnologias sustentaveis eficiencia energetica",
            "parcerias com universidades e centros de pesquisa",
        ),
        target_words=1200,
        prompt_strategy="narrative",
    ),
    ReportSectionTemplate(
        key="auditorias",
        title="Auditorias e Avaliações",
        order=9,
        heading_level=1,
        directory_keys=("auditorias-e-avaliacoes",),
        gri_codes=("GRI 2-5", "GRI 2-27"),
        rag_queries=(
            "auditorias internas e externas relatórios",
            "certificacoes ISO selos ambientais",
            "nao conformidades e planos de acao",
        ),
        target_words=1400,
        prompt_strategy="narrative",
    ),
    ReportSectionTemplate(
        key="comunicacao",
        title="Comunicação e Transparência",
        order=10,
        heading_level=1,
        directory_keys=("comunicacao-e-transparencia",),
        gri_codes=("GRI 2-3", "GRI 2-28", "GRI 417-3"),
        rag_queries=(
            "plano de comunicacao ESG e canais",
            "publicacoes relatorios boletins institucionais",
            "transparencia e divulgacao publica",
        ),
        target_words=1000,
        prompt_strategy="narrative",
    ),
    ReportSectionTemplate(
        key="temas-materiais",
        title="Temas Materiais e Matriz de Materialidade",
        order=11,
        heading_level=1,
        directory_keys=(
            "visao-estrategica-de-sustentabilidade",
            "relatorios-e-normas",
        ),
        gri_codes=("GRI 3-1", "GRI 3-2", "GRI 3-3"),
        rag_queries=(
            "temas materiais metodologia de priorizacao",
            "matriz de materialidade impactos e stakeholders",
            "principios de materialidade GRI",
        ),
        target_words=1800,
        prompt_strategy="materialidade",
    ),
    ReportSectionTemplate(
        key="plano-acao",
        title="Plano de Ação e Priorização de Temas Materiais",
        order=12,
        heading_level=1,
        directory_keys=(
            "visao-estrategica-de-sustentabilidade",
            "governanca-corporativa",
        ),
        gri_codes=("GRI 3-3",),
        rag_queries=(
            "plano de acao metas e responsaveis",
            "monitoramento de temas materiais indicadores",
            "priorizacao de riscos e oportunidades ESG",
        ),
        target_words=1600,
        prompt_strategy="plano_acao",
    ),
    ReportSectionTemplate(
        key="alinhamento-ods",
        title="Alinhamento das Ações aos ODS",
        order=13,
        heading_level=1,
        directory_keys=(
            "visao-estrategica-de-sustentabilidade",
            "gestao-ambiental",
            "desempenho-social",
            "gestao-de-desempenho-economico",
        ),
        gri_codes=("GRI 2-22", "GRI 3-3"),
        rag_queries=(
            "objetivos de desenvolvimento sustentavel ODS compromisso",
            "metas Agenda 2030 e alinhamento estrategico",
            "contribuicoes organizacionais aos ODS",
        ),
        target_words=1500,
        prompt_strategy="ods_alignment",
    ),
    ReportSectionTemplate(
        key="sumario-gri",
        title="Sumário GRI",
        order=14,
        heading_level=1,
        # no RAG queries — this section is produced deterministically from
        # accumulated in-text matches + batch LLM classification of unmatched codes
        directory_keys=(),
        gri_codes=(),
        rag_queries=(),
        target_words=800,
        prompt_strategy="gri_summary",
    ),
)


def get_section(key: str) -> ReportSectionTemplate | None:
    for section in REPORT_SECTIONS:
        if section.key == key:
            return section
    return None
