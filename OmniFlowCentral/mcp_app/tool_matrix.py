from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Dict, List


def _bootstrap_shared_imports() -> None:
    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))


_bootstrap_shared_imports()

from shared.tool_specs import TOOL_SPECS


@dataclass(frozen=True)
class ToolMigrationEntry:
    tool: str
    phase: str
    mcp_name: str
    status: str
    notes: str


_DEFAULT_PHASE = "phase-3"


_PHASE_CONFIG: Dict[str, ToolMigrationEntry] = {
    "query_dataset": ToolMigrationEntry(
        tool="query_dataset",
        phase="phase-1",
        mcp_name="query_dataset",
        status="implemented",
        notes="MVP parity for PrawoL core retrieval.",
    ),
    "dataset_search": ToolMigrationEntry(
        tool="dataset_search",
        phase="phase-1",
        mcp_name="dataset_search",
        status="implemented",
        notes="MVP parity for dataset discovery.",
    ),
    "saos_search": ToolMigrationEntry(
        tool="saos_search",
        phase="phase-2",
        mcp_name="saos_search",
        status="implemented",
        notes="Read-only external SAOS API search for on-demand judgments.",
    ),
    "saos_detail": ToolMigrationEntry(
        tool="saos_detail",
        phase="phase-2",
        mcp_name="saos_detail",
        status="implemented",
        notes="Read-only external SAOS API detail fetch by judgment id.",
    ),
    "eli_acts_query": ToolMigrationEntry(
        tool="eli_acts_query",
        phase="phase-2",
        mcp_name="eli_acts_query",
        status="planned",
        notes="Deprecated in backend; keep only for compatibility if needed.",
    ),
    "list_blobs": ToolMigrationEntry(
        tool="list_blobs",
        phase="phase-3",
        mcp_name="list_blobs",
        status="planned",
        notes="Read-only file namespace operations for authenticated users.",
    ),
    "read_blob": ToolMigrationEntry(
        tool="read_blob",
        phase="phase-3",
        mcp_name="read_blob",
        status="planned",
        notes="Read operations after auth hardening.",
    ),
    "read_many_blobs": ToolMigrationEntry(
        tool="read_many_blobs",
        phase="phase-3",
        mcp_name="read_many_blobs",
        status="planned",
        notes="Potentially expensive; keep behind stricter limits.",
    ),
    "get_filtered_data": ToolMigrationEntry(
        tool="get_filtered_data",
        phase="phase-3",
        mcp_name="get_filtered_data",
        status="planned",
        notes="Read-only data extraction; auth and rate-limit required.",
    ),
    "upload_blob": ToolMigrationEntry(
        tool="upload_blob",
        phase="phase-4",
        mcp_name="upload_blob",
        status="deferred",
        notes="Write operation; requires OAuth and explicit confirmation UX.",
    ),
    "delete_blob": ToolMigrationEntry(
        tool="delete_blob",
        phase="phase-4",
        mcp_name="delete_blob",
        status="deferred",
        notes="Destructive operation; requires elevated guardrails.",
    ),
    "upload_data_or_file": ToolMigrationEntry(
        tool="upload_data_or_file",
        phase="phase-4",
        mcp_name="upload_data_or_file",
        status="deferred",
        notes="Write operation; requires OAuth and audit logging.",
    ),
    "add_new_data": ToolMigrationEntry(
        tool="add_new_data",
        phase="phase-4",
        mcp_name="add_new_data",
        status="deferred",
        notes="Write operation; requires OAuth and confirmation.",
    ),
    "update_data_entry": ToolMigrationEntry(
        tool="update_data_entry",
        phase="phase-4",
        mcp_name="update_data_entry",
        status="deferred",
        notes="Write operation; requires OAuth and confirmation.",
    ),
    "remove_data_entry": ToolMigrationEntry(
        tool="remove_data_entry",
        phase="phase-4",
        mcp_name="remove_data_entry",
        status="deferred",
        notes="Destructive write; requires OAuth and higher assurance.",
    ),
    "manage_files": ToolMigrationEntry(
        tool="manage_files",
        phase="phase-4",
        mcp_name="manage_files",
        status="deferred",
        notes="Mixed write/destructive operations; post-MVP scope.",
    ),
}


def build_tool_migration_matrix() -> List[ToolMigrationEntry]:
    rows: List[ToolMigrationEntry] = []
    for tool_name in sorted(TOOL_SPECS.keys()):
        row = _PHASE_CONFIG.get(tool_name)
        if row is None:
            row = ToolMigrationEntry(
                tool=tool_name,
                phase=_DEFAULT_PHASE,
                mcp_name=tool_name,
                status="planned",
                notes="Not explicitly classified yet.",
            )
        rows.append(row)
    return rows
