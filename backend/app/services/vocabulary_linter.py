"""Post-process linter that enforces the Prompt-Mestre's controlled vocabulary.

- Forbidden terms: replaced in-place with ``[termo removido]`` and reported.
- Controlled terms: flagged as a warning when they appear without a numeric
  context nearby. Controlled terms ARE allowed with data; this just surfaces
  cases worth reviewing.
- Recommended terms: not enforced — this is just for display/future tooling.

Matching is case-insensitive and whole-word. Hits do not match inside GRI code
parentheticals like ``(GRI 305-1)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


FORBIDDEN_TERMS: tuple[str, ...] = (
    "orgulho",
    "protagonismo",
    "transformador",
    "inovador",
    "referência absoluta",
    "liderança sem evidência",
)

CONTROLLED_TERMS: tuple[str, ...] = (
    "compromisso",
    "avanço",
    "redução",
    "eficiência",
)

RECOMMENDED_TERMS: tuple[str, ...] = (
    "materialidade",
    "abordagem de gestão",
    "governança",
    "indicador",
    "desempenho",
    "rastreabilidade",
    "impacto",
    "risco",
    "melhoria contínua",
)


# Matches any numeric-ish context within ~40 chars of a term: raw numbers,
# percentages, currency, units. Used to decide whether a controlled term is
# supported by data nearby.
_NUMERIC_CONTEXT_PATTERN = re.compile(
    r"(?:\d[\d\.,]*\s*(?:%|kwh|m³|m3|tco2?e?|t|kg|l|r\$|r\$))|(?:\d[\d\.,]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class LinterWarning:
    """A non-fatal finding: controlled term used without evident data nearby."""

    term: str
    position: int
    excerpt: str


@dataclass(frozen=True, slots=True)
class LinterRemoval:
    """A fatal finding: forbidden term was present and replaced."""

    term: str
    position: int
    original: str


@dataclass(frozen=True, slots=True)
class LinterResult:
    cleaned_content: str
    removals: list[LinterRemoval]
    warnings: list[LinterWarning]


def _compile_term_pattern(terms: Iterable[str]) -> re.Pattern[str]:
    # escape each term, wrap with word boundaries, join with alternation
    escaped = [re.escape(term) for term in terms]
    if not escaped:
        # never matches
        return re.compile(r"(?!x)x")
    pattern = r"(?<![\wÀ-ÿ])(" + "|".join(escaped) + r")(?![\wÀ-ÿ])"
    return re.compile(pattern, re.IGNORECASE)


_FORBIDDEN_PATTERN = _compile_term_pattern(FORBIDDEN_TERMS)
_CONTROLLED_PATTERN = _compile_term_pattern(CONTROLLED_TERMS)


def _has_numeric_context(content: str, position: int, window: int = 40) -> bool:
    start = max(0, position - window)
    end = min(len(content), position + window)
    return bool(_NUMERIC_CONTEXT_PATTERN.search(content[start:end]))


def _context_excerpt(content: str, position: int, window: int = 40) -> str:
    start = max(0, position - window)
    end = min(len(content), position + window)
    snippet = content[start:end].strip().replace("\n", " ")
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return f"{prefix}{snippet}{suffix}"


def lint(content: str) -> LinterResult:
    """Run the vocabulary linter on a section's generated content."""
    removals: list[LinterRemoval] = []

    def _replace_forbidden(match: re.Match[str]) -> str:
        removals.append(
            LinterRemoval(
                term=match.group(0),
                position=match.start(),
                original=match.group(0),
            )
        )
        return "[termo removido]"

    cleaned = _FORBIDDEN_PATTERN.sub(_replace_forbidden, content)

    warnings: list[LinterWarning] = []
    for match in _CONTROLLED_PATTERN.finditer(cleaned):
        if _has_numeric_context(cleaned, match.start()):
            continue
        warnings.append(
            LinterWarning(
                term=match.group(0),
                position=match.start(),
                excerpt=_context_excerpt(cleaned, match.start()),
            )
        )

    return LinterResult(
        cleaned_content=cleaned,
        removals=removals,
        warnings=warnings,
    )
