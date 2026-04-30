from __future__ import annotations

import os
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, ToolAnnotations
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from .adapter import (
    run_dataset_search,
    run_fetch,
    run_query_dataset,
    run_saos_detail,
    run_saos_search,
    run_search,
)
from .tool_matrix import build_tool_migration_matrix


mcp = FastMCP(
    "PrawoL MCP",
    instructions=(
        "Read-only legal retrieval MCP adapter for OmniFlowCentral. "
        "Primary tools: query_dataset, dataset_search."
    ),
    stateless_http=True,
    json_response=True,
)

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
    idempotentHint=True,
)


@mcp.custom_route("/.well-known/{path:path}", methods=["GET"], include_in_schema=False)
async def openai_apps_domain_verification(request: Request) -> Response:
    """
    Domain verification endpoint for ChatGPT Apps.

    It serves the verification token as plain text for any
    '/.well-known/openai-apps-*' path required by the verifier.
    """
    path = (request.path_params.get("path") or "").strip()
    if not path.startswith("openai-apps-"):
        return PlainTextResponse("not found", status_code=404)

    token = os.environ.get("OPENAI_APPS_DOMAIN_VERIFICATION_TOKEN", "").strip()
    if not token:
        return PlainTextResponse("verification token not configured", status_code=404)

    return PlainTextResponse(token, status_code=200)


@mcp.tool(
    title="Query legal dataset",
    description=(
        "Use this when you need filtered legal records from a dataset "
        "(acts, judgments, metadata). Do not use for arbitrary web search."
    ),
    annotations=READ_ONLY_ANNOTATIONS,
)
def query_dataset(
    dataset: str,
    q: Optional[str] = None,
    limit: int = 10,
    fetch_content: bool = False,
    year: Optional[int] = None,
    publisher: Optional[str] = None,
    status: Optional[str] = None,
    court: Optional[str] = None,
    court_type: Optional[str] = None,
    pageId: Optional[str] = None,
    recordIndex: Optional[int] = None,
    content_slice: Optional[Dict[str, int]] = None,
) -> CallToolResult:
    payload: Dict[str, Any] = {
        "dataset": dataset,
        "q": q,
        "limit": limit,
        "fetch_content": fetch_content,
        "year": year,
        "publisher": publisher,
        "status": status,
        "court": court,
        "court_type": court_type,
        "pageId": pageId,
        "recordIndex": recordIndex,
        "content_slice": content_slice,
    }
    clean_payload = {key: value for key, value in payload.items() if value is not None}
    return run_query_dataset(clean_payload)


@mcp.tool(
    title="Search user dataset index",
    description=(
        "Use this when you need user-oriented dataset lookup by text, tags, "
        "category, or date range. Do not use for retrieving full legal act text."
    ),
    annotations=READ_ONLY_ANNOTATIONS,
)
def dataset_search(
    user_id: Optional[str] = None,
    q: Optional[str] = None,
    tags_any: Optional[list[str]] = None,
    tags_all: Optional[list[str]] = None,
    category: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
) -> CallToolResult:
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "q": q,
        "tags_any": tags_any,
        "tags_all": tags_all,
        "category": category,
        "since": since,
        "until": until,
        "limit": limit,
        "cursor": cursor,
    }
    clean_payload = {key: value for key, value in payload.items() if value is not None}
    return run_dataset_search(clean_payload)


@mcp.tool(
    title="Search SAOS judgments",
    description=(
        "Search the external SAOS judgments API on demand. Use after ELI grounding "
        "when you need current case law without maintaining a full local mirror."
    ),
    annotations=READ_ONLY_ANNOTATIONS,
)
def saos_search(
    q: Optional[str] = None,
    limit: int = 10,
    page: int = 0,
    page_size: Optional[int] = None,
    court_type: Optional[str] = None,
    judgment_date_from: Optional[str] = None,
    judgment_date_to: Optional[str] = None,
    case_number: Optional[str] = None,
) -> CallToolResult:
    payload: Dict[str, Any] = {
        "q": q,
        "limit": limit,
        "page": page,
        "page_size": page_size,
        "court_type": court_type,
        "judgment_date_from": judgment_date_from,
        "judgment_date_to": judgment_date_to,
        "case_number": case_number,
    }
    clean_payload = {key: value for key, value in payload.items() if value is not None}
    return run_saos_search(clean_payload)


@mcp.tool(
    title="Fetch SAOS judgment detail",
    description="Fetch metadata and content for one SAOS judgment by id returned from saos_search.",
    annotations=READ_ONLY_ANNOTATIONS,
)
def saos_detail(judgment_id: str) -> CallToolResult:
    return run_saos_detail({"judgment_id": judgment_id})


@mcp.tool(
    title="Search legal acts (MCP-compatible)",
    description=(
        "Use this when the client expects search-style MCP results "
        "(id/title/url). Read-only wrapper over query_dataset."
    ),
    annotations=READ_ONLY_ANNOTATIONS,
)
def search(query: str, dataset: str = "eli_acts", limit: int = 10) -> CallToolResult:
    return run_search({"query": query, "dataset": dataset, "limit": limit})


@mcp.tool(
    title="Fetch legal document by id",
    description=(
        "Use this when you already have a canonical MCP document id and need "
        "the full text payload. Read-only deterministic fetch."
    ),
    annotations=READ_ONLY_ANNOTATIONS,
)
def fetch(id: str, dataset: str = "eli_acts") -> CallToolResult:
    return run_fetch({"id": id, "dataset": dataset})


@mcp.tool(
    title="Get migration matrix",
    description=(
        "Use this for operational visibility of GPT App migration status. "
        "Returns tool/phase/status mapping only."
    ),
    annotations=READ_ONLY_ANNOTATIONS,
)
def migration_matrix() -> dict[str, list[dict[str, str]]]:
    entries = build_tool_migration_matrix()
    return {
        "tools": [
            {
                "tool": item.tool,
                "phase": item.phase,
                "mcp_name": item.mcp_name,
                "status": item.status,
                "notes": item.notes,
            }
            for item in entries
        ]
    }


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
