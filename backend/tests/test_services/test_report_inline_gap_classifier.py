"""Tests for the inline gap classifier service fallback behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.report_inline_gap_classifier import (
    InlineGapClassificationResult,
    InlineGapClassifierContext,
    _fallback_classify,
    classify_inline_gaps,
)


def test_fallback_classify_removes_inline_gap_diagnostics_and_keeps_enquadramento() -> (
    None
):
    ctx = InlineGapClassifierContext(
        section_key="a-empresa",
        section_title="A Empresa",
        gri_codes=("GRI 2-1", "GRI 2-2", "GRI 2-6"),
        content=(
            "A organização foi fundada em 2016 e atua no setor de logística. "
            "A ausência de dados quantitativos específicos limita a profundidade "
            "da análise.\n\n"
            "Não foram disponibilizados dados específicos sobre o número de "
            "unidades, colaboradores, frota ou mercados atendidos.\n\n"
            "Enquadramento ESG e normativo\n"
            "- Pilares ESG: E / S / G\n"
            "- GRI aplicável: GRI 2-1 | GRI 2-2 | GRI 2-6\n"
        ),
    )

    result = _fallback_classify(ctx)

    assert (
        "A ausência de dados quantitativos específicos limita"
        not in result.cleaned_content
    )
    assert (
        "Não foram disponibilizados dados específicos sobre"
        not in result.cleaned_content
    )
    assert "A organização foi fundada em 2016" in result.cleaned_content
    assert "Enquadramento ESG e normativo" in result.cleaned_content

    assert len(result.findings) == 2
    assert result.findings[0].severity == "warning"
    assert result.findings[0].priority == "medium"
    assert result.findings[0].missing_data_type is not None
    assert (
        result.findings[0].suggested_document
        == "Documento institucional, planilha operacional ou evidência primária da pasta da seção"
    )
    assert result.findings[0].related_gri_codes == [
        "GRI 2-1",
        "GRI 2-2",
        "GRI 2-6",
    ]


def test_fallback_classify_returns_original_content_when_no_pattern_matches() -> None:
    content = (
        "A organização foi fundada em 2016 e opera no setor de logística.\n\n"
        "Enquadramento ESG e normativo\n"
        "- Pilares ESG: E\n"
        "- GRI aplicável: GRI 2-1\n"
    )
    ctx = InlineGapClassifierContext(
        section_key="a-empresa",
        section_title="A Empresa",
        gri_codes=("GRI 2-1",),
        content=content,
    )

    result = _fallback_classify(ctx)

    assert result.cleaned_content == content.strip()
    assert result.findings == []


def test_fallback_classify_preserves_original_when_everything_matches_patterns() -> (
    None
):
    ctx = InlineGapClassifierContext(
        section_key="a-empresa",
        section_title="A Empresa",
        gri_codes=("GRI 2-1", "GRI 2-2", "GRI 2-6"),
        content=(
            "A ausência de indicadores quantitativos impede a apresentação de "
            "métricas relacionadas ao desempenho operacional.\n\n"
            "Recomenda-se a implementação futura de indicadores compatíveis com "
            "os GRI 2-1, 2-2 e 2-6 para aprimorar a rastreabilidade."
        ),
    )

    result = _fallback_classify(ctx)

    # Safety behavior: if all content is stripped, fallback returns the original
    # content rather than an empty string.
    assert result.cleaned_content == ctx.content.strip()
    assert len(result.findings) == 2
    assert all(finding.priority == "medium" for finding in result.findings)
    assert all(
        finding.related_gri_codes == ["GRI 2-1", "GRI 2-2", "GRI 2-6"]
        for finding in result.findings
    )


# ---------- Realistic content regression (Cooperliquidos example) ----------

COOPERLIQUIDOS_CONTENT = """\
A Cooperliquidos constitui uma organização de grande porte atuante no setor de transportes, com sede localizada em Canoas, Rio Grande do Sul. Fundada em data não especificada no contexto disponível, a empresa desenvolve suas atividades principais no transporte de líquidos, operando em âmbito regional e possivelmente nacional, conforme a abrangência típica do setor e porte declarado. A natureza jurídica e o registro formal da Cooperliquidos não foram informados, assim como o escopo operacional detalhado, o que limita a precisão sobre a extensão exata de suas operações e unidades administrativas ou logísticas (GRI 2-1).

A materialidade da Cooperliquidos está associada a temas ambientais e sociais relevantes para o setor de transportes. A organização reconhece a importância estratégica desses temas para sua operação e para a cadeia de valor na qual está inserida, embora não haja evidências disponíveis que detalhem políticas, processos ou resultados relacionados a esses aspectos. A ausência de indicadores quantitativos e dados específicos limita a análise do desempenho e da gestão desses temas materiais (GRI 2-1).

A abordagem de gestão da Cooperliquidos, em termos de governança, políticas e processos, não está detalhada nas informações fornecidas. Não foram apresentadas evidências sobre estruturas de governança específicas, sistemas de gestão ambiental, protocolos de segurança ou mecanismos de monitoramento e controle operacional. A ausência desses dados impede a avaliação da maturidade institucional e da capacidade da organização em gerir os temas materiais identificados (GRI 2-2).

Quanto aos resultados e desempenho do período de referência, não foram disponibilizados dados quantitativos ou qualitativos que permitam mensurar o impacto das operações da Cooperliquidos. A inexistência de indicadores, métricas ou metas relacionadas aos temas materiais impede a análise do desempenho e a verificação de eventuais avanços ou desvios em relação a objetivos estratégicos ou normativos. Essa limitação compromete a transparência e a auditabilidade do relato institucional (GRI 2-2).

Indicadores compatíveis com os temas materiais poderiam incluir, para o aspecto ambiental, consumo de energia, emissões de gases de efeito estufa, consumo e gestão de água. A ausência desses dados evidencia a necessidade de desenvolvimento e implementação de sistemas de coleta e monitoramento para futuras divulgações (GRI 2-2).

A interpretação gerencial e o impacto estratégico da Cooperliquidos não podem ser avaliados com base nas informações disponíveis. Sem dados sobre a gestão, resultados ou indicadores, não é possível inferir o grau de integração dos temas materiais na estratégia corporativa. Essa lacuna limita a compreensão do posicionamento da organização frente aos desafios do setor (GRI 2-6).

Em termos de evolução e maturidade institucional, a Cooperliquidos apresenta um relato preliminar com evidentes lacunas informacionais, indicando estágio inicial na formalização e divulgação de dados ESG. A organização poderia se beneficiar da adoção dos GRI Standards para estruturar seu relato de sustentabilidade.

Enquadramento ESG e normativo
- Pilares ESG: E / S / G
- GRI aplicável: GRI 2-1 | GRI 2-2 | GRI 2-6
- ODS relacionados: ODS 6, ODS 7, ODS 12\
"""

# Anti-pattern phrases that MUST be caught by the fallback regex catalog.
COOPERLIQUIDOS_ANTIPATTERNS = [
    "em data não especificada no contexto disponível",
    "possivelmente nacional",
    "conforme a abrangência típica do setor",
    "não foram informados",
    "limita a precisão",
    "embora não haja evidências disponíveis que detalhem",
    "A ausência de indicadores quantitativos e dados específicos limita",
    "não está detalhada nas informações fornecidas",
    "Não foram apresentadas evidências sobre",
    "A ausência desses dados impede",
    "não foram disponibilizados dados quantitativos ou qualitativos",
    "A inexistência de indicadores, métricas ou metas",
    "Essa limitação compromete a transparência",
    "Indicadores compatíveis com os temas materiais poderiam incluir",
    "evidencia a necessidade de desenvolvimento",
    "não podem ser avaliados com base nas informações disponíveis",
    "Sem dados sobre a gestão",
    "Essa lacuna limita a compreensão",
    "apresenta um relato preliminar com evidentes lacunas informacionais",
    "indicando estágio inicial na formalização",
    "poderia se beneficiar da adoção",
]


def test_fallback_classify_catches_cooperliquidos_antipatterns() -> None:
    ctx = InlineGapClassifierContext(
        section_key="a-empresa",
        section_title="A Empresa",
        gri_codes=("GRI 2-1", "GRI 2-2", "GRI 2-6"),
        content=COOPERLIQUIDOS_CONTENT,
    )

    result = _fallback_classify(ctx)

    for phrase in COOPERLIQUIDOS_ANTIPATTERNS:
        assert phrase not in result.cleaned_content, (
            f"Anti-pattern still in cleaned output: {phrase!r}"
        )

    # Factual content must survive.
    assert "Cooperliquidos" in result.cleaned_content
    assert "Canoas" in result.cleaned_content
    assert "setor de transportes" in result.cleaned_content

    # Enquadramento block preserved.
    assert "Enquadramento ESG e normativo" in result.cleaned_content

    # Must produce findings.
    assert len(result.findings) >= 10


@pytest.mark.asyncio
async def test_safety_net_catches_residuals_after_llm_passthrough() -> None:
    """When the LLM returns content unchanged, the safety net regex catches residuals."""
    ctx = InlineGapClassifierContext(
        section_key="a-empresa",
        section_title="A Empresa",
        gri_codes=("GRI 2-1",),
        content=(
            "A organização atua no setor de logística. "
            "A ausência de dados quantitativos específicos limita a análise. "
            "Recomenda-se a implementação de indicadores compatíveis.\n\n"
            "Enquadramento ESG e normativo\n- Pilares ESG: E\n"
        ),
    )

    # Fake LLM that returns content unchanged (simulating a too-permissive LLM).
    llm_passthrough = InlineGapClassificationResult(
        cleaned_content=ctx.content,
        findings=[],
    )

    from app.core.config import Settings

    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://x:x@localhost/x",
        aws_access_key_id="x",
        aws_secret_access_key="x",
        openai_api_key="x",
        pinecone_api_key="x",
    )

    with patch("langchain_openai.ChatOpenAI") as mock_chat_cls:
        mock_llm = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_llm.ainvoke.return_value = llm_passthrough
        mock_chat_cls.return_value = mock_llm

        result = await classify_inline_gaps(settings=settings, ctx=ctx)

    # Safety net must have caught the residuals.
    assert "A ausência de dados quantitativos" not in result.cleaned_content
    assert "Recomenda-se a implementação" not in result.cleaned_content
    assert "Enquadramento ESG e normativo" in result.cleaned_content
    assert len(result.findings) >= 2
