#!/usr/bin/env python3
"""
Fast Azurite/Azure container scan based on blob *metadata only* (name + size + last_modified).

Use-cases:
- confirm where ELI/SAOS data actually lives (prefix discovery)
- estimate download/extraction remaining work from counts
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from azure.storage.blob import BlobServiceClient


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _split_prefix(name: str, depth: int) -> str:
    parts = [p for p in name.split("/") if p]
    if not parts:
        return ""
    return "/".join(parts[:depth]) + "/"


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan blob container by metadata (no content downloads).")
    ap.add_argument(
        "--conn",
        default=os.environ.get("AZURITE_CONN", ""),
        help="Storage connection string (env: AZURITE_CONN).",
    )
    ap.add_argument(
        "--container",
        default=os.environ.get("AZURITE_CONTAINER", "omniflowcentralcustomgpt"),
        help="Container name.",
    )
    ap.add_argument("--depth", type=int, default=3, help="Prefix grouping depth.")
    ap.add_argument("--max", type=int, default=1_000_000, help="Safety cap on blobs iterated.")
    ap.add_argument(
        "--focus",
        action="append",
        default=[],
        help="Only count blobs starting with this prefix (repeatable).",
    )
    ap.add_argument("--out", default="tmp/azurite_meta_scan_report.json", help="Output JSON path.")
    args = ap.parse_args()

    conn = (args.conn or "").strip()
    if not conn:
        raise SystemExit("Missing --conn (or AZURITE_CONN env var).")

    focus = [p for p in (args.focus or []) if p]
    svc = BlobServiceClient.from_connection_string(conn)
    cont = svc.get_container_client(args.container)

    total = 0
    total_bytes = 0
    suffix_counts = Counter()
    top_prefix = Counter()
    largest: List[Tuple[int, str]] = []

    def push_largest(size: int, name: str, k: int = 30) -> None:
        largest.append((size, name))
        largest.sort(reverse=True)
        del largest[k:]

    for i, b in enumerate(cont.list_blobs()):
        if i >= args.max:
            break
        name = b.name
        if focus and not any(name.startswith(p) for p in focus):
            continue
        size = int(getattr(b, "size", 0) or 0)
        total += 1
        total_bytes += size
        top_prefix[_split_prefix(name, int(args.depth))] += 1
        ext = ""
        if "." in name.rsplit("/", 1)[-1]:
            ext = "." + name.rsplit(".", 1)[-1].lower()
        suffix_counts[ext] += 1
        push_largest(size, name)

    report: Dict[str, Any] = {
        "tool": "azurite_meta_scan",
        "generated_at": _now_iso(),
        "container": args.container,
        "focus": focus,
        "depth": args.depth,
        "max": args.max,
        "blobs_counted": total,
        "bytes_total": total_bytes,
        "top_prefixes": top_prefix.most_common(100),
        "suffix_counts": suffix_counts.most_common(),
        "largest": [{"bytes": s, "name": n} for s, n in largest],
    }

    out_path = args.out
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({"out": out_path, "blobs_counted": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

