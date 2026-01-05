"""
Shared tool catalog and alias mapping for tool handlers.

Purpose:
- Define canonical tool names (aligned with Central/App2).
- Provide alias resolution for Beta/App1 legacy names.
- Central place to evolve param requirements and caps without changing handlers yet.

This module is intentionally minimal in Phase 1:
- No runtime validation beyond alias normalization.
- No behavior changes to handlers; callers opt-in to use helpers here.
"""
from __future__ import annotations

from typing import Dict, List

from shared.blob_ops import (
    DEFAULT_MAX_BYTES_PER_FILE,
    DEFAULT_MAX_RESULTS,
    DEFAULT_READ_MANY_FILES,
    DEFAULT_TAIL_BYTES,
    DEFAULT_TAIL_LINES,
    MAX_RESULTS_LIMIT,
)

# Canonical tool list (initially CRUD-only); expand as we onboard more tools.
CANONICAL_TOOLS: List[str] = [
    "read_blob",
    "list_blobs",
]

# Tool name aliases (legacy -> canonical)
TOOL_ALIASES: Dict[str, str] = {
    "read_blob_file": "read_blob",
}


# Per-tool parameter aliases (legacy -> canonical). Keys are canonical tool names.
PARAM_ALIASES: Dict[str, Dict[str, str]] = {
    "read_blob": {
        "file_name": "name",
    },
    "list_blobs": {
        # keep include_meta as an optional flag; no rename needed
    },
}


# Param metadata (minimal, descriptive only for now; enforcement lives in handlers)
TOOL_PARAM_SPECS: Dict[str, Dict[str, object]] = {
    "read_blob": {
        "required": {"name": "string (relative blob path)"},
        "optional": {},
        "caps": {
            "max_bytes_per_file": DEFAULT_MAX_BYTES_PER_FILE,
        },
    },
    "list_blobs": {
        "required": {},
        "optional": {
            "prefix": "string",
            "max_results": f"int (default {DEFAULT_MAX_RESULTS}, max {MAX_RESULTS_LIMIT})",
            "timeout_seconds": "int (default 10, max 60)",
            "include_meta": "bool (optional, Beta legacy)",
        },
        "caps": {
            "max_results": MAX_RESULTS_LIMIT,
            "timeout_seconds": 60,
        },
    },
    # Template for future tools (reference only, not active):
    "_read_many_template": {
        "required": {"files": "array[string]"},
        "optional": {
            "tail_lines": f"int (default {DEFAULT_TAIL_LINES})",
            "tail_bytes": f"int (default {DEFAULT_TAIL_BYTES})",
            "max_bytes_per_file": f"int (default {DEFAULT_MAX_BYTES_PER_FILE})",
            "parse_json": "bool (default true)",
            "max_files": f"int (default {DEFAULT_READ_MANY_FILES})",
        },
    },
}


def canonical_tool_name(name: str) -> str:
    """Return the canonical tool name, applying alias mapping when needed."""
    if not name:
        return ""
    normalized = str(name).strip()
    return TOOL_ALIASES.get(normalized, normalized)


def apply_param_aliases(tool: str, params: Dict[str, object] | None) -> Dict[str, object]:
    """Return a new dict with parameter aliases resolved to canonical names."""
    resolved_tool = canonical_tool_name(tool)
    mapping = PARAM_ALIASES.get(resolved_tool, {})
    if not params:
        return {}
    normalized = dict(params)
    for legacy, canonical in mapping.items():
        if legacy in normalized and canonical not in normalized:
            normalized[canonical] = normalized.pop(legacy)
    return normalized
