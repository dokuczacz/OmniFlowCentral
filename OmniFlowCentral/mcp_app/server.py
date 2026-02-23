from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult

from .adapter import run_dataset_search, run_fetch, run_query_dataset, run_search
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
def search(query: str, dataset: str = "eli_acts", limit: int = 10) -> CallToolResult:
    return run_search({"query": query, "dataset": dataset, "limit": limit})


@mcp.tool()
def fetch(id: str, dataset: str = "eli_acts") -> CallToolResult:
    return run_fetch({"id": id, "dataset": dataset})


@mcp.tool()
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
