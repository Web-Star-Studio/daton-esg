"""Shared helpers for Server-Sent Event (SSE) streams.

The codebase has two SSE producers (langgraph_chat_service, report_service) that
each defined their own ``_sse_event``. New SSE consumers should import from here.
"""

from __future__ import annotations

import json
from typing import Any


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def sse_event(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json_dumps(data)}\n\n".encode("utf-8")
