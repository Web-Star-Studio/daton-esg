from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ParsedDocumentResult:
    extracted_text: str
    parsed_payload: dict[str, Any]


__all__ = ["ParsedDocumentResult"]
