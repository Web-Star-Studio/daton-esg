from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import Any

import boto3
import pdfplumber
from botocore.config import Config

from app.core.config import Settings, get_settings
from app.services.parsing import ParsedDocumentResult

logger = logging.getLogger(__name__)

TEXTRACT_POLL_INTERVAL_SECONDS = 2.0
TEXTRACT_JOB_TIMEOUT_SECONDS = 120.0
TEXTRACT_SUCCESS_STATUSES = {"SUCCEEDED", "PARTIAL_SUCCESS"}


def _build_textract_client(settings: Settings):
    client_kwargs = {
        "service_name": "textract",
        "region_name": settings.aws_textract_region or settings.aws_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "config": Config(retries={"max_attempts": 2, "mode": "standard"}),
    }

    if settings.aws_endpoint_url and "localstack" not in settings.aws_endpoint_url:
        client_kwargs["endpoint_url"] = settings.aws_endpoint_url

    return boto3.client(**client_kwargs)


def should_use_local_pdf_parser(settings: Settings | None = None) -> bool:
    current_settings = settings or get_settings()
    provider = current_settings.document_parsing_pdf_provider
    if provider == "local":
        return True
    if provider == "textract":
        return False

    endpoint = (current_settings.aws_endpoint_url or "").lower()
    return current_settings.environment == "development" or "localstack" in endpoint


def _normalize_cell(cell: Any) -> str | None:
    if cell is None:
        return None

    if isinstance(cell, str):
        normalized = cell.strip()
        return normalized or None

    return str(cell)


def _build_pdf_result_from_textract_blocks(
    blocks: list[dict[str, Any]],
    *,
    provider: str,
    job_id: str | None = None,
) -> ParsedDocumentResult:
    block_map = {block["Id"]: block for block in blocks if "Id" in block}
    line_blocks = [
        block
        for block in blocks
        if block.get("BlockType") == "LINE" and block.get("Text")
    ]
    line_blocks.sort(
        key=lambda block: (
            block.get("Page", 1),
            block.get("Geometry", {}).get("BoundingBox", {}).get("Top", 0),
        )
    )

    pages_map: dict[int, dict[str, Any]] = {}
    for line_block in line_blocks:
        page_number = int(line_block.get("Page", 1))
        page_payload = pages_map.setdefault(
            page_number,
            {
                "page_number": page_number,
                "text_lines": [],
                "tables": [],
            },
        )
        page_payload["text_lines"].append(line_block["Text"])

    tables_payload = []

    for table_block in blocks:
        if table_block.get("BlockType") != "TABLE":
            continue

        cells: dict[int, dict[int, str | None]] = {}
        relationships = table_block.get("Relationships", [])
        child_ids = [
            child_id
            for relationship in relationships
            if relationship.get("Type") == "CHILD"
            for child_id in relationship.get("Ids", [])
        ]

        for child_id in child_ids:
            cell_block = block_map.get(child_id)
            if not cell_block or cell_block.get("BlockType") != "CELL":
                continue

            text_fragments = []
            for relationship in cell_block.get("Relationships", []):
                if relationship.get("Type") != "CHILD":
                    continue
                for text_id in relationship.get("Ids", []):
                    text_block = block_map.get(text_id)
                    if not text_block:
                        continue
                    if text_block.get("BlockType") == "WORD":
                        text_fragments.append(text_block.get("Text", ""))
                    elif text_block.get("BlockType") == "SELECTION_ELEMENT":
                        if text_block.get("SelectionStatus") == "SELECTED":
                            text_fragments.append("X")

            row_index = int(cell_block.get("RowIndex", 1))
            column_index = int(cell_block.get("ColumnIndex", 1))
            cells.setdefault(row_index, {})[column_index] = (
                " ".join(fragment for fragment in text_fragments if fragment).strip()
                or None
            )

        if not cells:
            continue

        max_columns = max(max(columns.keys()) for columns in cells.values())
        rows = []
        for row_index in sorted(cells):
            rows.append(
                [cells[row_index].get(column) for column in range(1, max_columns + 1)]
            )

        header = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []
        page_number = int(table_block.get("Page", 1))
        table_payload = {
            "page_number": page_number,
            "header": header,
            "rows": data_rows,
        }
        tables_payload.append(table_payload)
        page_payload = pages_map.setdefault(
            page_number,
            {
                "page_number": page_number,
                "text_lines": [],
                "tables": [],
            },
        )
        page_payload["tables"].append(
            {
                "header": header,
                "rows": data_rows,
            }
        )

    pages_payload = []
    extracted_chunks: list[str] = []
    for page_number in sorted(pages_map):
        page_payload = pages_map[page_number]
        page_text = "\n".join(page_payload.pop("text_lines")).strip()
        if page_text:
            extracted_chunks.append(page_text)
        for table in page_payload["tables"]:
            if table["header"]:
                extracted_chunks.append(
                    " | ".join(cell or "" for cell in table["header"]).strip()
                )
            for row in table["rows"]:
                extracted_chunks.append(" | ".join(cell or "" for cell in row).strip())
        pages_payload.append(
            {
                "page_number": page_number,
                "text": page_text or None,
                "tables": page_payload["tables"],
            }
        )

    return ParsedDocumentResult(
        extracted_text="\n\n".join(
            chunk for chunk in extracted_chunks if chunk
        ).strip(),
        parsed_payload={
            "provider": provider,
            "job_id": job_id,
            "pages": pages_payload,
            "tables": tables_payload,
        },
    )


def parse_pdf_locally(file_bytes: bytes) -> ParsedDocumentResult:
    pages_payload: list[dict[str, Any]] = []
    extracted_chunks: list[str] = []

    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            tables = []
            for raw_table in page.extract_tables() or []:
                normalized_rows = [
                    [_normalize_cell(cell) for cell in row]
                    for row in raw_table
                    if row is not None
                ]
                filtered_rows = [
                    row
                    for row in normalized_rows
                    if any(cell not in {None, ""} for cell in row)
                ]
                if not filtered_rows:
                    continue

                header = filtered_rows[0]
                rows = filtered_rows[1:] if len(filtered_rows) > 1 else []
                tables.append(
                    {
                        "header": header,
                        "rows": rows,
                    }
                )

                if header:
                    extracted_chunks.append(
                        " | ".join(cell or "" for cell in header).strip()
                    )
                for row in rows:
                    extracted_chunks.append(
                        " | ".join(cell or "" for cell in row).strip()
                    )

            if page_text:
                extracted_chunks.append(page_text)

            pages_payload.append(
                {
                    "page_number": page_index,
                    "text": page_text or None,
                    "tables": tables,
                }
            )

    return ParsedDocumentResult(
        extracted_text="\n\n".join(
            chunk for chunk in extracted_chunks if chunk
        ).strip(),
        parsed_payload={
            "provider": "local",
            "pages": pages_payload,
            "tables": [table for page in pages_payload for table in page["tables"]],
        },
    )


async def _start_textract_document_analysis(
    client,
    *,
    bucket_name: str,
    key: str,
) -> str:
    response = await asyncio.to_thread(
        client.start_document_analysis,
        DocumentLocation={"S3Object": {"Bucket": bucket_name, "Name": key}},
        FeatureTypes=["TABLES"],
    )
    return response["JobId"]


async def _get_textract_document_analysis_page(
    client,
    *,
    job_id: str,
    next_token: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"JobId": job_id}
    if next_token:
        kwargs["NextToken"] = next_token
    return await asyncio.to_thread(client.get_document_analysis, **kwargs)


async def parse_pdf_with_textract(
    *,
    bucket_name: str,
    key: str,
    settings: Settings | None = None,
) -> ParsedDocumentResult:
    current_settings = settings or get_settings()
    client = _build_textract_client(current_settings)
    job_id = await _start_textract_document_analysis(
        client,
        bucket_name=bucket_name,
        key=key,
    )
    logger.info("pdf_parser.textract_job_started", extra={"job_id": job_id, "key": key})

    start_time = asyncio.get_running_loop().time()
    blocks: list[dict[str, Any]] = []

    while True:
        if (
            asyncio.get_running_loop().time() - start_time
        ) > TEXTRACT_JOB_TIMEOUT_SECONDS:
            raise TimeoutError(
                f"Textract analysis timed out for document {key} (job {job_id})"
            )

        response = await _get_textract_document_analysis_page(client, job_id=job_id)
        job_status = response.get("JobStatus")
        logger.info(
            "pdf_parser.textract_job_polled",
            extra={"job_id": job_id, "job_status": job_status, "key": key},
        )

        if job_status == "IN_PROGRESS":
            await asyncio.sleep(TEXTRACT_POLL_INTERVAL_SECONDS)
            continue

        if job_status not in TEXTRACT_SUCCESS_STATUSES:
            status_message = response.get("StatusMessage") or "Textract analysis failed"
            raise RuntimeError(
                f"Textract analysis failed for document {key} "
                f"(job {job_id}): {status_message}"
            )

        blocks.extend(response.get("Blocks", []))
        next_token = response.get("NextToken")
        while next_token:
            paged_response = await _get_textract_document_analysis_page(
                client,
                job_id=job_id,
                next_token=next_token,
            )
            blocks.extend(paged_response.get("Blocks", []))
            next_token = paged_response.get("NextToken")

        return _build_pdf_result_from_textract_blocks(
            blocks,
            provider="textract",
            job_id=job_id,
        )


async def parse_pdf_document(
    *,
    file_bytes: bytes | None = None,
    bucket_name: str | None = None,
    key: str | None = None,
    settings: Settings | None = None,
) -> ParsedDocumentResult:
    current_settings = settings or get_settings()

    if should_use_local_pdf_parser(current_settings):
        if file_bytes is None:
            raise ValueError("file_bytes is required for local PDF parsing")
        logger.info("pdf_parser.local")
        return parse_pdf_locally(file_bytes)

    logger.info("pdf_parser.textract")
    if not bucket_name or not key:
        raise ValueError("bucket_name and key are required for Textract PDF parsing")
    return await parse_pdf_with_textract(
        bucket_name=bucket_name,
        key=key,
        settings=current_settings,
    )
