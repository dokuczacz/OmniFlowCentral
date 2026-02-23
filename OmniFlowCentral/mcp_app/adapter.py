from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

try:
    from mcp.types import CallToolResult, TextContent
except Exception:  # pragma: no cover - fallback for non-MCP test environments
    @dataclass
    class TextContent:
        type: str
        text: str

    @dataclass
    class CallToolResult:
        content: list[TextContent]
        structuredContent: Dict[str, Any] | None = None
        _meta: Dict[str, Any] | None = None
        isError: bool = False


def _bootstrap_shared_imports() -> None:
    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))


_bootstrap_shared_imports()

from shared.blob_ops import ToolError
from shared.data_ops import dataset_search, query_dataset


def _default_user_id() -> str:
    candidate = os.environ.get("OMNIFLOW_DEFAULT_USER_ID", "").strip()
    return candidate or "public"


def _ok_result(message: str, structured: Dict[str, Any], meta: Dict[str, Any]) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=message)],
        structuredContent=structured,
        _meta=meta,
    )


def _error_result(error_code: str, message: str, details: Dict[str, Any] | None = None) -> CallToolResult:
    payload: Dict[str, Any] = {
        "status": "error",
        "error": {
            "code": error_code,
            "message": message,
        },
    }
    if details:
        payload["error"]["details"] = details
    return CallToolResult(
        isError=True,
        content=[TextContent(type="text", text=message)],
        structuredContent=payload,
        _meta={"error": payload["error"]},
    )


def run_query_dataset(arguments: Dict[str, Any]) -> CallToolResult:
    try:
        result = query_dataset(params=arguments)
        dataset = str(arguments.get("dataset") or result.get("dataset") or "")
        total_returned = int(result.get("total_returned") or len(result.get("hits") or []))
        message = f"query_dataset returned {total_returned} hit(s) for dataset '{dataset}'."
        return _ok_result(
            message=message,
            structured=result,
            meta={
                "source": "omniflowcentral",
                "tool": "query_dataset",
                "dataset": dataset,
            },
        )
    except ToolError as exc:
        return _error_result(exc.code, exc.message, exc.details)
    except Exception as exc:
        return _error_result("UPSTREAM_ERROR", "query_dataset failed.", {"detail": str(exc)})


def run_dataset_search(arguments: Dict[str, Any]) -> CallToolResult:
    user_id = str(arguments.get("user_id") or _default_user_id()).strip() or _default_user_id()
    params = dict(arguments)
    params.pop("user_id", None)
    try:
        result = dataset_search(user_id=user_id, params=params)
        total_returned = len(result.get("hits") or [])
        message = f"dataset_search returned {total_returned} hit(s) for user '{user_id}'."
        return _ok_result(
            message=message,
            structured=result,
            meta={
                "source": "omniflowcentral",
                "tool": "dataset_search",
                "user_id": user_id,
            },
        )
    except ToolError as exc:
        return _error_result(exc.code, exc.message, exc.details)
    except Exception as exc:
        return _error_result("UPSTREAM_ERROR", "dataset_search failed.", {"detail": str(exc)})


def _canonical_hit_id(hit: Dict[str, Any], dataset: str) -> str:
    page_id = str(hit.get("pageId") or hit.get("ELI") or "").strip()
    record_index = hit.get("recordIndex")
    if record_index is None:
        record_index = hit.get("pos")
    if page_id and record_index is not None:
        return f"{dataset}:{page_id}:{record_index}"
    if page_id:
        return f"{dataset}:{page_id}"
    return f"{dataset}:{hash(json.dumps(hit, ensure_ascii=False, sort_keys=True))}"


def _canonical_hit_url(hit: Dict[str, Any], dataset: str) -> str:
    existing_url = str(hit.get("url") or "").strip()
    if existing_url:
        return existing_url
    page_id = str(hit.get("pageId") or hit.get("ELI") or "").strip()
    if page_id and dataset == "eli_acts":
        return f"https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id={page_id}"
    if page_id:
        return f"omniflow://{dataset}/{page_id}"
    return f"omniflow://{dataset}/record"


def run_search(arguments: Dict[str, Any]) -> CallToolResult:
    dataset = str(arguments.get("dataset") or "eli_acts").strip() or "eli_acts"
    query = str(arguments.get("query") or "").strip()
    limit = arguments.get("limit", 10)

    result = run_query_dataset(
        {
            "dataset": dataset,
            "q": query,
            "limit": limit,
            "fetch_content": False,
        }
    )
    if result.isError:
        return result

    structured = result.structuredContent if isinstance(result.structuredContent, dict) else {}
    hits = structured.get("hits") or []
    search_payload = {
        "results": [
            {
                "id": _canonical_hit_id(hit, dataset),
                "title": str(hit.get("title") or hit.get("displayAddress") or hit.get("display_name") or "Untitled"),
                "url": _canonical_hit_url(hit, dataset),
            }
            for hit in hits
        ]
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(search_payload, ensure_ascii=False))],
        structuredContent={
            "status": "success",
            "dataset": dataset,
            "query": query,
            "count": len(search_payload["results"]),
        },
        _meta={
            "source": "omniflowcentral",
            "tool": "search",
            "raw_hits": hits,
        },
    )


def run_fetch(arguments: Dict[str, Any]) -> CallToolResult:
    dataset = str(arguments.get("dataset") or "eli_acts").strip() or "eli_acts"
    doc_id = str(arguments.get("id") or "").strip()
    if not doc_id:
        return _error_result("MISSING_PARAM", "Parameter 'id' is required.")

    parts = doc_id.split(":")
    page_id = None
    record_index = None
    if len(parts) >= 2:
        page_id = parts[1]
    if len(parts) >= 3:
        try:
            record_index = int(parts[2])
        except ValueError:
            record_index = None

    query_args: Dict[str, Any] = {
        "dataset": dataset,
        "limit": 1,
        "fetch_content": True,
    }
    if page_id:
        query_args["pageId"] = page_id
    if record_index is not None:
        query_args["recordIndex"] = record_index

    result = run_query_dataset(query_args)
    if result.isError:
        return result

    structured = result.structuredContent if isinstance(result.structuredContent, dict) else {}
    hits = structured.get("hits") or []
    if not hits:
        return _error_result("NOT_FOUND", f"Document '{doc_id}' not found.")

    hit = hits[0]
    payload = {
        "id": doc_id,
        "title": str(hit.get("title") or hit.get("displayAddress") or hit.get("display_name") or "Untitled"),
        "text": str(
            hit.get("_fullContent")
            or hit.get("_fullText")
            or hit.get("_fullTextExcerpt")
            or hit.get("title")
            or ""
        ),
        "url": _canonical_hit_url(hit, dataset),
        "metadata": {
            "dataset": dataset,
            "pageId": hit.get("pageId") or hit.get("ELI"),
            "recordIndex": hit.get("recordIndex") if hit.get("recordIndex") is not None else hit.get("pos"),
        },
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        structuredContent={
            "status": "success",
            "dataset": dataset,
            "id": doc_id,
            "found": True,
        },
        _meta={
            "source": "omniflowcentral",
            "tool": "fetch",
            "raw_hit": hit,
        },
    )
