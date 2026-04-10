from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import anthropic

from app.core.config import Settings, get_settings
from app.models.enums import ClassificationConfidence

logger = logging.getLogger(__name__)

ESG_CATEGORY_OPTIONS = [
    "Visão e Estratégia",
    "Governança",
    "Ambiental",
    "Social",
    "Econômico",
    "Stakeholders",
    "Inovação",
    "Normas",
    "Comunicação",
    "Auditorias",
]
CONFIDENCE_OPTIONS = [member.value for member in ClassificationConfidence]


@dataclass(slots=True)
class ClassificationInput:
    extraction_id: str
    source_kind: str
    source_snippet: str
    source_locator: dict[str, Any] | None


@dataclass(slots=True)
class ClassificationOutput:
    extraction_id: str
    label: str | None
    original_value: str | None
    original_unit: str | None
    original_period: str | None
    original_esg_category: str | None
    confidence: ClassificationConfidence


def _strip_json_fence(payload: str) -> str:
    normalized = payload.strip()
    if normalized.startswith("```"):
        normalized = normalized.split("\n", 1)[-1]
        if normalized.endswith("```"):
            normalized = normalized.rsplit("\n", 1)[0]
    return normalized.strip()


def _extract_json_payload(payload: str) -> list[dict[str, Any]]:
    normalized = _strip_json_fence(payload)
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        start = normalized.find("[")
        end = normalized.rfind("]")
        if start == -1 or end == -1 or start >= end:
            raise
        parsed = json.loads(normalized[start : end + 1])

    if not isinstance(parsed, list):
        raise ValueError("Anthropic classification response must be a JSON array")

    if any(not isinstance(item, dict) for item in parsed):
        raise ValueError(
            "Anthropic classification response must be a JSON array of objects"
        )

    return parsed


def _normalize_confidence(value: str | None) -> ClassificationConfidence:
    normalized = (value or "").strip().lower()
    if not normalized:
        return ClassificationConfidence.MEDIUM
    if normalized == ClassificationConfidence.HIGH.value:
        return ClassificationConfidence.HIGH
    if normalized == ClassificationConfidence.MEDIUM.value:
        return ClassificationConfidence.MEDIUM
    if normalized == ClassificationConfidence.LOW.value:
        return ClassificationConfidence.LOW
    raise ValueError(f"Unknown confidence value: {value!r}")


def _normalize_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        normalized = str(value).strip()
        return normalized or None
    raise ValueError(f"Unsupported scalar type: {type(value).__name__}")


def _normalize_category(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _build_prompt(extractions: list[ClassificationInput]) -> str:
    extraction_payload = [
        {
            "id": extraction.extraction_id,
            "source_kind": extraction.source_kind,
            "source_locator": extraction.source_locator,
            "source_snippet": extraction.source_snippet,
        }
        for extraction in extractions
    ]

    return (
        "Classifique cada extração em uma categoria ESG da lista: "
        f"{', '.join(ESG_CATEGORY_OPTIONS)}, ou null se não for classificável. "
        "Para cada item, retorne um array JSON com os campos: "
        "id, esg_category, confidence, label, value, unit, period. "
        "Use confidence apenas como high, medium ou low. "
        "Use label curto quando houver um dado identificável. "
        "Quando não houver valor numérico explícito, use null em value/unit/period. "
        "Se a extração não pertencer a nenhuma categoria ESG, "
        "use null em esg_category. "
        "Responda com JSON puro, sem markdown.\n\n"
        f"Extrações:\n{json.dumps(extraction_payload, ensure_ascii=False)}"
    )


_client: anthropic.AsyncAnthropic | None = None
_client_key_hash: int | None = None


def _get_client(settings: Settings) -> anthropic.AsyncAnthropic:
    global _client, _client_key_hash

    if not settings.anthropic_api_key:
        raise RuntimeError("Anthropic API key is required for ESG classification")

    key = settings.anthropic_api_key.get_secret_value()
    key_hash = hash(key)

    if _client is None or _client_key_hash != key_hash:
        _client = anthropic.AsyncAnthropic(api_key=key)
        _client_key_hash = key_hash

    return _client


async def _call_anthropic(prompt: str, settings: Settings) -> str:
    client = _get_client(settings)

    try:
        message = await client.messages.create(
            model=settings.classification_model,
            max_tokens=8192,
            temperature=settings.classification_temperature,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
    except anthropic.AuthenticationError as e:
        raise RuntimeError("Invalid Anthropic API key") from e
    except anthropic.RateLimitError as e:
        raise RuntimeError("Anthropic rate limit exceeded — try again shortly") from e
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Could not connect to Anthropic API: {e}") from e

    text_blocks = [block.text for block in message.content if block.type == "text"]
    if not text_blocks:
        raise ValueError("Anthropic response did not contain a text block")

    return "\n".join(text_blocks).strip()


CLASSIFICATION_BATCH_SIZE = 50


async def _classify_batch(
    extractions: list[ClassificationInput],
    settings: Settings,
) -> list[ClassificationOutput]:
    prompt = _build_prompt(extractions)
    raw_response = await _call_anthropic(prompt, settings)
    parsed_response = _extract_json_payload(raw_response)
    response_by_id = {str(item.get("id")): item for item in parsed_response}
    results: list[ClassificationOutput] = []

    for extraction in extractions:
        item = response_by_id.get(extraction.extraction_id)
        if item is None:
            raise ValueError(
                "Anthropic classification response missing "
                f"extraction {extraction.extraction_id}"
            )

        category = _normalize_category(item.get("esg_category"))
        if category is not None and category not in ESG_CATEGORY_OPTIONS:
            raise ValueError(
                "Anthropic classification returned unsupported "
                f"category for {extraction.extraction_id}"
            )

        results.append(
            ClassificationOutput(
                extraction_id=extraction.extraction_id,
                label=_normalize_scalar(item.get("label")),
                original_value=_normalize_scalar(item.get("value")),
                original_unit=_normalize_scalar(item.get("unit")),
                original_period=_normalize_scalar(item.get("period")),
                original_esg_category=category,
                confidence=_normalize_confidence(item.get("confidence")),
            )
        )

    return results


async def classify_document_extractions(
    extractions: list[ClassificationInput],
    *,
    settings: Settings | None = None,
) -> list[ClassificationOutput]:
    if not extractions:
        return []

    current_settings = settings or get_settings()
    results: list[ClassificationOutput] = []

    for i in range(0, len(extractions), CLASSIFICATION_BATCH_SIZE):
        batch = extractions[i : i + CLASSIFICATION_BATCH_SIZE]
        batch_results = await _classify_batch(batch, current_settings)
        results.extend(batch_results)

    logger.info(
        "document_classification.completed",
        extra={
            "extractions": len(results),
            "batches": (len(extractions) + CLASSIFICATION_BATCH_SIZE - 1)
            // CLASSIFICATION_BATCH_SIZE,
            "model": current_settings.classification_model,
        },
    )
    return results
