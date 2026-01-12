#!/usr/bin/env python3
"""
Fetch SAOS court reference metadata and publish it to Azure blob storage.

Publishes into:
  users/public/datasets/saos/judgments/metadata/commonCourts.json
  users/public/datasets/saos/judgments/metadata/courts.json

The "commonCourts" endpoint is paged; this script follows rel=next until done.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from azure.storage.blob import BlobServiceClient, ContentSettings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_all_common_courts(base_url: str, *, page_size: int, timeout: float, max_pages: int) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/dump/commonCourts?pageSize={page_size}&pageNumber=0"
    items: List[Dict[str, Any]] = []
    pages = 0

    while url:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        payload = r.json()
        items.extend(payload.get("items") or [])
        pages += 1
        if 0 < max_pages <= pages:
            break
        next_url = None
        for link in payload.get("links") or []:
            if link.get("rel") == "next" and link.get("href"):
                next_url = link["href"]
                break
        url = next_url

    return {
        "source": {"base_url": base_url, "endpoint": "/dump/commonCourts"},
        "generated_at": _now_iso(),
        "page_size": page_size,
        "pages_fetched": pages,
        "items": items,
    }


def _derive_courts(common: Dict[str, Any]) -> Dict[str, Any]:
    # Minimal, stable court list derived from the commonCourts dump.
    courts = []
    for c in common.get("items") or []:
        courts.append(
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "type": c.get("type"),
                "code": c.get("code"),
                "parentCourt": (c.get("parentCourt") or {}).get("id") if isinstance(c.get("parentCourt"), dict) else c.get("parentCourt"),
            }
        )
    return {
        "source": {"derived_from": "commonCourts.json"},
        "generated_at": _now_iso(),
        "items": courts,
    }


def _upload_json(container, blob_name: str, payload: Dict[str, Any]) -> None:
    container.get_blob_client(blob_name).upload_blob(
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json; charset=utf-8"),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish SAOS metadata to Azure blob storage.")
    ap.add_argument("--connection-string", default=os.environ.get("AZURE_STORAGE_CONNECTION_STRING", ""))
    ap.add_argument("--container-name", default="omniflowcentralcustomgpt")
    ap.add_argument("--saos-base-url", default="https://www.saos.org.pl/api")
    ap.add_argument("--page-size", type=int, default=200)
    ap.add_argument("--max-pages", type=int, default=0, help="0 = no limit")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--dst-prefix", default="users/public/datasets/saos/judgments/metadata")
    args = ap.parse_args()

    cs = (args.connection_string or "").strip()
    if not cs:
        raise SystemExit("Missing --connection-string / AZURE_STORAGE_CONNECTION_STRING")

    svc = BlobServiceClient.from_connection_string(cs)
    container = svc.get_container_client(args.container_name)

    max_pages = int(args.max_pages)
    common = _fetch_all_common_courts(
        args.saos_base_url,
        page_size=int(args.page_size),
        timeout=float(args.timeout),
        max_pages=max_pages if max_pages > 0 else -1,
    )
    courts = _derive_courts(common)

    dst = args.dst_prefix.rstrip("/")
    common_blob = f"{dst}/commonCourts.json"
    courts_blob = f"{dst}/courts.json"

    _upload_json(container, common_blob, common)
    _upload_json(container, courts_blob, courts)

    print(
        {
            "tool": "saos_publish_metadata",
            "finished_at": _now_iso(),
            "commonCourts_blob": common_blob,
            "courts_blob": courts_blob,
            "commonCourts_items": len(common.get("items") or []),
            "pages_fetched": common.get("pages_fetched"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

