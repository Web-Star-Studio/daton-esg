"""LLM-assisted classifier for inline anti-pattern diagnostics in report sections.

This module runs a second-pass structured review over a generated report
section. Its goal is to identify meta-diagnostic sentences that should not
appear in the final narrative, such as:
- explicit statements about missing data
- operational recommendations to the consultant
- process/error-like commentary
- "this section is limited because..." style caveats
- speculation without evidence ("possivelmente", "presumivelmente")

The classifier returns:
1. a cleaned version of the content
2. structured findings that can be converted into report gaps

Implementation notes:
- Primary path: structured LLM classification using ChatOpenAI.
- Safety net: after the LLM pass, fallback regex patterns are run on the
  cleaned output to catch any residual anti-patterns the LLM missed.
- Fallback path: deterministic pattern matching, used only when the classifier
  is unavailable or fails, so report generation remains resilient.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Each entry: (regex, title, recommendation, missing_data_type)
_INLINE_GAP_PATTERNS: tuple[tuple[re.Pattern[str], str, str, str], ...] = (
    # --- Group 1: explicit absence / missing data declarations ---
    (
        re.compile(
            r"(?i)\b(?:a |essa )?aus[eê]ncia (?:de |atual de |desses? )"
            r"(?:dados|indicadores|informaç[oõ]es|evidências|m[eé]tricas|metas)"
        ),
        "Declaração de ausência de dados removida",
        "Complementar a pasta da seção com os dados ou evidências citados.",
        "Dado factual ou quantitativo ausente",
    ),
    (
        re.compile(
            r"(?i)\bn[aãoõ]o (?:foram |est[aá] |h[aá] |é possível )"
            r"(?:informad|reportad|disponibilizad|apresentad|divulgad|detalhad|"
            r"fornecid|identificad)"
        ),
        "Constatação de dado não fornecido removida",
        "Solicitar ao cliente a documentação ou evidência faltante.",
        "Documento ou evidência não fornecida",
    ),
    (
        re.compile(
            r"(?i)\b(?:a |essa )?inexist[eê]ncia de "
            r"(?:dados|indicadores|informaç[oõ]es|metas|m[eé]tricas|pol[ií]ticas)"
        ),
        "Constatação de inexistência de dados removida",
        "Indicar a necessidade de coleta na página de lacunas.",
        "Dado factual ou quantitativo ausente",
    ),
    (
        re.compile(
            r"(?i)\bsem (?:dados|informaç[oõ]es|evidências|indicadores) sobre\b"
        ),
        "Constatação de ausência de dados removida",
        "Documentar a lacuna e solicitar evidências.",
        "Dado factual ou quantitativo ausente",
    ),
    (
        re.compile(
            r"(?i)\bn[aãoõ]o (?:há|haja|houve|existe[m]?) "
            r"(?:dados|indicadores|informaç[oõ]es|evidências|documentaç[aã]o|"
            r"metas|registro)"
        ),
        "Constatação de dado inexistente removida",
        "Complementar a pasta da seção com as evidências correspondentes.",
        "Documento ou evidência não fornecida",
    ),
    (
        re.compile(
            r"(?i)\b(?:embora |ainda que )?n[aãoõ]o (?:haja|há|houve) "
            r"(?:evidências|documentaç[aã]o|dados)"
        ),
        "Ressalva concessiva sobre falta de evidência removida",
        "Indicar na página de lacunas e solicitar documentação ao cliente.",
        "Documento ou evidência não fornecida",
    ),
    (
        re.compile(r"(?i)\bem (?:data|período) n[aãoõ]o especificad[oa]\b"),
        "Informação temporal não disponível removida",
        "Solicitar ao cliente a data ou período exato.",
        "Data ou período de referência",
    ),
    (
        re.compile(
            r"(?i)\bn[aãoõ]o (?:pode[m]? ser|é possível) "
            r"(?:avaliado|mensurado|verificado|analisado|inferido)"
        ),
        "Constatação de impossibilidade analítica removida",
        "Registrar a limitação como lacuna e orientar a coleta de dados.",
        "Dado factual ou quantitativo ausente",
    ),
    # --- Group 2: analytical limitation caveats ---
    (
        re.compile(
            r"(?i)\b(?:limita|impede|compromete|inviabiliza) "
            r"(?:a |o )?(?:precis[aã]o|an[aá]lise|compreens[aã]o|avaliaç[aã]o|"
            r"profundidade|transparência|auditabilidade|rastreabilidade|"
            r"verificaç[aã]o|mensuraç[aã]o)"
        ),
        "Diagnóstico de limitação analítica removido",
        "Converter a limitação em lacuna acionável.",
        "Evidência organizacional insuficiente",
    ),
    (
        re.compile(
            r"(?i)\bessa (?:lacuna|limitaç[aã]o|carência) (?:limita|impede|compromete)\b"
        ),
        "Diagnóstico de limitação removido",
        "Registrar como lacuna estruturada na página dedicada.",
        "Evidência organizacional insuficiente",
    ),
    # --- Group 3: speculation without evidence ---
    (
        re.compile(r"(?i)\b(?:presumivelmente|possivelmente|provavelmente)\b"),
        "Especulação sem evidência removida",
        "Remover o trecho especulativo ou substituir por dados concretos.",
        "Evidência documental para afirmação",
    ),
    (
        re.compile(
            r"(?i)\b(?:conforme (?:a abrangência|o porte|o perfil|a natureza) "
            r"típic[oa] d[eo]|é plausível que|seria esperado que)"
        ),
        "Inferência genérica sem evidência removida",
        "Substituir por fatos documentados ou registrar como lacuna.",
        "Evidência documental para afirmação",
    ),
    # --- Group 4: operational recommendations to consultant ---
    (
        re.compile(
            r"(?i)\brecomenda-se (?:a |o )?"
            r"(?:implementaç[aã]o|coleta|estruturaç[aã]o|adoç[aã]o|desenvolvimento)"
        ),
        "Recomendação operacional removida do corpo da seção",
        "Apresentar recomendações na página de lacunas.",
        "Estruturação de indicadores ou processos",
    ),
    (
        re.compile(
            r"(?i)\b(?:a organizaç[aã]o |a empresa )?"
            r"(?:poderia se beneficiar|seria beneficiad[oa]) (?:da |de |pela )"
        ),
        "Sugestão operacional removida do corpo da seção",
        "Registrar a sugestão como lacuna de melhoria.",
        "Estruturação de indicadores ou processos",
    ),
    (
        re.compile(
            r"(?i)\b(?:evidencia|sugere|indica) a necessidade de "
            r"(?:desenvolvimento|implementaç[aã]o|aprimoramento|"
            r"estruturaç[aã]o|fortalecimento)"
        ),
        "Meta-diagnóstico sobre necessidade de desenvolvimento removido",
        "Registrar como lacuna e sugerir ações específicas.",
        "Estruturação de indicadores ou processos",
    ),
    # --- Group 5: meta-commentary about the report itself ---
    (
        re.compile(
            r"(?i)\b(?:apresenta|indica[m]?|denota) (?:um )?(?:relato preliminar|"
            r"est[aá]gio inicial|evidentes? lacunas? informaciona)"
        ),
        "Meta-comentário sobre maturidade do relato removido",
        "Registrar a maturidade como lacuna estruturada.",
        "Maturidade do relato ESG",
    ),
    (
        re.compile(
            r"(?i)\bindicadores compat[ií]veis "
            r"(?:com os temas materiais )?poderiam incluir\b"
        ),
        "Sugestão genérica de indicadores removida do corpo",
        "Mover sugestões de indicadores para a página de lacunas.",
        "Estruturação de indicadores ou processos",
    ),
)

_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[\.\!\?])\s+")


class InlineGapFinding(BaseModel):
    """Single anti-pattern finding extracted from a generated section."""

    excerpt: str = Field(min_length=1)
    title: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    severity: Literal["info", "warning", "critical"] = "warning"
    priority: Literal["low", "medium", "high"] = "medium"
    missing_data_type: str | None = None
    suggested_document: str | None = None
    related_gri_codes: list[str] = Field(default_factory=list)


class InlineGapClassificationResult(BaseModel):
    """Structured output of the inline-gap classifier."""

    cleaned_content: str = Field(min_length=1)
    findings: list[InlineGapFinding] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class InlineGapClassifierContext:
    """Inputs used to classify a single generated section."""

    section_key: str
    section_title: str
    gri_codes: tuple[str, ...]
    content: str


def _build_system_prompt() -> str:  # noqa: E501
    return """\
Você é um classificador especializado em pós-processar seções de um relatório ESG preliminar.

Sua função é detectar e REMOVER do texto final frases e períodos que sejam anti-padrão — ou seja, que NÃO devem aparecer no relatório publicável. Esses trechos são diagnósticos internos, constatações de ausência de dado, limitações analíticas, especulação sem evidência, recomendações operacionais ao consultor, ou meta-comentários sobre o próprio relato.

TAXONOMIA DE ANTI-PADRÕES — remova qualquer frase que contenha:

1. DECLARAÇÃO DE AUSÊNCIA: "não foram informados/reportados/disponibilizados/apresentados/divulgados/fornecidos", "não há/haja/houve evidências/documentação/dados/indicadores/informações/metas/registro", "sem dados/informações/evidências sobre", "a ausência/inexistência de dados/indicadores/informações/métricas/políticas", "não está detalhada/detalhado", "em data não especificada no contexto disponível".
2. LIMITAÇÃO ANALÍTICA: "limita a precisão/análise/compreensão/avaliação/profundidade/transparência/auditabilidade", "impede a avaliação/análise/mensuração/verificação", "não podem ser avaliados com base nas informações disponíveis", "essa lacuna/limitação/carência limita/impede/compromete", "compromete a transparência/auditabilidade do relato".
3. ESPECULAÇÃO SEM EVIDÊNCIA: "possivelmente", "presumivelmente", "provavelmente", "conforme a abrangência/porte/perfil típico do setor", "é plausível que", "seria esperado que", "idealmente".
4. RECOMENDAÇÃO OPERACIONAL: "recomenda-se a implementação/coleta/estruturação/adoção/desenvolvimento", "a organização poderia se beneficiar", "seria beneficiada pela adoção de", "evidencia/sugere/indica a necessidade de desenvolvimento/implementação/aprimoramento/estruturação".
5. META-COMENTÁRIO: "apresenta um relato preliminar com evidentes lacunas informacionais", "indicando estágio inicial na formalização", "indicadores compatíveis poderiam incluir", comentários sobre a maturidade do relato ou sobre o processo de elaboração.

DIRETRIZ FUNDAMENTAL: na dúvida entre manter e remover, PREFIRA REMOVER. O consultor revisa os findings na página de lacunas e pode restaurar se necessário. Deixar anti-padrão no texto publicável é pior do que removê-lo indevidamente.

EXEMPLOS BEFORE/AFTER:

BEFORE: "A organização atua no setor de logística, com sede em Canoas. A natureza jurídica e o registro formal da Cooperliquidos não foram informados, assim como o escopo operacional detalhado, o que limita a precisão sobre a extensão exata de suas operações (GRI 2-1)."
AFTER (cleaned): "A organização atua no setor de logística, com sede em Canoas (GRI 2-1)."
FINDING: excerpt="A natureza jurídica e o registro formal da Cooperliquidos não foram informados, assim como o escopo operacional detalhado, o que limita a precisão sobre a extensão exata de suas operações", title="Dados jurídicos e operacionais não informados", missing_data_type="Natureza jurídica, registro formal, escopo operacional", suggested_document="Contrato social, CNPJ, organograma operacional", related_gri_codes=["GRI 2-1"], severity="warning", priority="high", recommendation="Solicitar ao cliente contrato social e documentação operacional."

BEFORE: "Os riscos endereçados incluem, presumivelmente, a gestão de recursos naturais, embora não haja documentação que descreva explicitamente as estratégias adotadas."
AFTER (cleaned): ""
FINDING 1: excerpt="Os riscos endereçados incluem, presumivelmente, a gestão de recursos naturais", title="Especulação sobre riscos sem evidência", ...
FINDING 2: excerpt="embora não haja documentação que descreva explicitamente as estratégias adotadas", title="Documentação de estratégias ausente", ...

SAÍDA: devolva JSON estruturado com cleaned_content e findings[].

Cada finding deve conter:
- excerpt: trecho exato removido (copie do original)
- title: resumo curto e acionável (pt-BR, 5-15 palavras)
- recommendation: ação recomendada ao consultor
- severity: info|warning|critical
- priority: low|medium|high
- missing_data_type: tipo de dado faltante (ex: "Natureza jurídica", "Indicadores quantitativos", "Política ambiental")
- suggested_document: documento/evidência que supriria a lacuna (ex: "Relatório de emissões GEE", "Contrato social")
- related_gri_codes: lista de códigos GRI diretamente afetados

REGRAS DE PRESERVAÇÃO:
- NÃO remova fatos organizacionais objetivos (nomes, datas, números, cidades, atividades descritas).
- NÃO remova o bloco "Enquadramento ESG e normativo" no final da seção.
- NÃO invente dados nem reescreva o conteúdo factual — apenas corte os anti-padrões.
- Se após a remoção um parágrafo ficar vazio ou sem sentido, remova-o inteiro.
- O cleaned_content deve ser natural, coeso e publicável — ajuste pontuação e conectivos quando necessário após remoções.
- Se não houver anti-padrões, devolva o conteúdo intacto e findings=[].
"""


def _build_user_prompt(ctx: InlineGapClassifierContext) -> str:
    gri_codes = ", ".join(ctx.gri_codes) if ctx.gri_codes else "nenhum"
    return (
        f"Seção: {ctx.section_title} ({ctx.section_key})\n"
        f"Códigos GRI relevantes: {gri_codes}\n\n"
        "Analise o conteúdo abaixo e remova trechos anti-padrão do corpo final.\n\n"
        "[CONTEÚDO]\n"
        f"{ctx.content}\n"
    )


def _strip_with_patterns(
    content: str,
    gri_codes: tuple[str, ...],
) -> tuple[str, list[InlineGapFinding]]:
    """Run the regex catalog over content, returning cleaned text + findings."""
    paragraphs = content.split("\n\n")
    cleaned_paragraphs: list[str] = []
    findings: list[InlineGapFinding] = []

    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        if paragraph.lstrip().startswith("Enquadramento ESG e normativo"):
            cleaned_paragraphs.append(paragraph)
            continue

        parts = _SENTENCE_SPLIT_PATTERN.split(paragraph.strip())
        kept_parts: list[str] = []

        for part in parts:
            stripped_part = part.strip()
            if not stripped_part:
                continue

            matched = False
            for pattern, title, recommendation, mdt in _INLINE_GAP_PATTERNS:
                if pattern.search(stripped_part):
                    findings.append(
                        InlineGapFinding(
                            excerpt=stripped_part,
                            title=title,
                            recommendation=recommendation,
                            severity="warning",
                            priority="medium",
                            missing_data_type=mdt,
                            suggested_document=(
                                "Documento institucional, planilha operacional ou "
                                "evidência primária da pasta da seção"
                            ),
                            related_gri_codes=list(gri_codes),
                        )
                    )
                    matched = True
                    break

            if not matched:
                kept_parts.append(stripped_part)

        if kept_parts:
            cleaned_paragraphs.append(" ".join(kept_parts))

    cleaned_content = "\n\n".join(cleaned_paragraphs).strip()
    return cleaned_content, findings


def _has_any_pattern(content: str) -> bool:
    """Quick check: does content contain any known anti-pattern?"""
    for pattern, *_ in _INLINE_GAP_PATTERNS:
        if pattern.search(content):
            return True
    return False


def _fallback_classify(
    ctx: InlineGapClassifierContext,
) -> InlineGapClassificationResult:
    """Deterministic fallback used only if the LLM classifier fails."""
    cleaned_content, findings = _strip_with_patterns(ctx.content, ctx.gri_codes)
    if not cleaned_content:
        cleaned_content = ctx.content.strip()

    return InlineGapClassificationResult(
        cleaned_content=cleaned_content,
        findings=findings,
    )


async def classify_inline_gaps(
    *,
    settings: Settings,
    ctx: InlineGapClassifierContext,
) -> InlineGapClassificationResult:
    """Classify and remove inline anti-pattern diagnostics from a section.

    Execution flow:
    1. Primary: LLM structured output → cleaned_content + findings.
    2. Safety net: regex sweep on LLM output catches residuals the LLM missed.
    3. Fallback: if LLM fails entirely, regex-only path runs on the original.

    This function is intentionally resilient. Failures in the classifier should
    never abort section generation.
    """
    if not ctx.content.strip():
        return InlineGapClassificationResult(cleaned_content="", findings=[])

    path = "fallback"
    llm_result: InlineGapClassificationResult | None = None

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.report_generation_model,
            temperature=0.0,
            max_completion_tokens=settings.report_generation_max_output_tokens,
            api_key=settings.openai_api_key,
        )

        structured_llm = llm.with_structured_output(InlineGapClassificationResult)

        response = await structured_llm.ainvoke(
            [
                SystemMessage(content=_build_system_prompt()),
                HumanMessage(content=_build_user_prompt(ctx)),
            ]
        )

        if isinstance(response, InlineGapClassificationResult):
            cleaned = response.cleaned_content.strip() or ctx.content.strip()
            llm_result = InlineGapClassificationResult(
                cleaned_content=cleaned,
                findings=response.findings,
            )
            path = "llm"
        else:
            logger.warning(
                "report.inline_gap_classifier_unexpected_response",
                extra={
                    "section_key": ctx.section_key,
                    "response_type": type(response).__name__,
                },
            )
    except Exception:
        logger.exception(
            "report.inline_gap_classifier_failed",
            extra={"section_key": ctx.section_key},
        )

    if llm_result is None:
        result = _fallback_classify(ctx)
    else:
        # Safety net: sweep the LLM output with regex to catch residuals.
        if _has_any_pattern(llm_result.cleaned_content):
            residual_cleaned, residual_findings = _strip_with_patterns(
                llm_result.cleaned_content, ctx.gri_codes
            )
            if not residual_cleaned:
                residual_cleaned = llm_result.cleaned_content
            result = InlineGapClassificationResult(
                cleaned_content=residual_cleaned,
                findings=list(llm_result.findings) + residual_findings,
            )
            path = "llm+safety_net"
        else:
            result = llm_result

    input_len = len(ctx.content)
    output_len = len(result.cleaned_content)
    logger.info(
        "report.inline_gap_classifier_run",
        extra={
            "section_key": ctx.section_key,
            "path": path,
            "input_length": input_len,
            "output_length": output_len,
            "findings_count": len(result.findings),
            "delta_ratio": round(1 - output_len / max(input_len, 1), 3),
        },
    )

    return result


def classification_result_to_json(
    result: InlineGapClassificationResult,
) -> str:
    """Small helper for debugging/logging tests if needed."""
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
