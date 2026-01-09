import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import requests
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


ELI_BASE_URL = "https://api.sejm.gov.pl/eli"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        parts: List[str] = []
        for page in doc:
            parts.append(page.get_text("text"))
        return "\n".join(parts).strip()
    finally:
        doc.close()


def _iter_eli_ids(index_text: str) -> List[str]:
    out: List[str] = []
    for line in index_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        eli_id = (obj.get("ELI") or obj.get("pageId") or "").strip()
        if eli_id:
            out.append(eli_id)
    return out


def _download_index(container, index_blob: str) -> str:
    raw = container.get_blob_client(index_blob).download_blob().readall()
    return raw.decode("utf-8", "replace")


def _upload_text(container, blob_name: str, text: str) -> None:
    container.get_blob_client(blob_name).upload_blob(
        text.encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type="text/plain; charset=utf-8"),
    )


def _fetch_pdf(eli_id: str, timeout: float) -> Tuple[Optional[bytes], Optional[str]]:
    url = f"{ELI_BASE_URL}/acts/{eli_id}/text.pdf"
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 404:
            return None, "404"
        r.raise_for_status()
        return r.content, None
    except Exception as e:
        return None, str(e)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Seed per-act extracted texts for a small set of ELI ids from an existing eli_acts index."
    )
    ap.add_argument(
        "--connection-string",
        default=os.environ.get("AZURE_STORAGE_CONNECTION_STRING", ""),
        help="Azure Storage connection string (env: AZURE_STORAGE_CONNECTION_STRING).",
    )
    ap.add_argument("--container-name", default="omniflowcentralcustomgpt")
    ap.add_argument(
        "--index-blob",
        default="users/public/datasets/eli_acts/index/acts_inforce_1.jsonl",
        help="NDJSON index blob to read ELI ids from.",
    )
    ap.add_argument(
        "--text-prefix",
        default="users/public/datasets/eli_acts/text",
        help="Prefix under which to write per-act .txt blobs.",
    )
    ap.add_argument("--limit", type=int, default=100, help="How many ids to seed.")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cs = (args.connection_string or "").strip()
    if not cs:
        raise SystemExit("Missing --connection-string (or AZURE_STORAGE_CONNECTION_STRING env var).")

    service = BlobServiceClient.from_connection_string(cs)
    container = service.get_container_client(args.container_name)

    index_text = _download_index(container, args.index_blob)
    ids = _iter_eli_ids(index_text)
    ids = ids[: max(0, int(args.limit))]

    summary: Dict[str, int] = {"ok": 0, "skipped": 0, "errors": 0}
    meta: Dict[str, object] = {
        "tool": "eli_seed_texts_from_index",
        "started_at": _now_iso(),
        "index_blob": args.index_blob,
        "text_prefix": args.text_prefix,
        "limit": args.limit,
        "counts": summary,
        "last_eli": None,
        "finished_at": None,
    }

    for eli_id in ids:
        meta["last_eli"] = eli_id
        out_blob = f"{args.text_prefix.rstrip('/')}/{eli_id}.txt"
        if args.verbose:
            print(f"ELI {eli_id} -> {out_blob}")

        pdf, err = _fetch_pdf(eli_id, args.timeout)
        if pdf is None:
            _upload_text(container, out_blob, f"[SKIPPED] no PDF/text available ({err})\n")
            summary["skipped"] += 1
            continue

        try:
            text = _extract_pdf_text(pdf)
            if not text.strip():
                _upload_text(container, out_blob, "[SKIPPED] extracted empty text\n")
                summary["skipped"] += 1
            else:
                _upload_text(container, out_blob, text)
                summary["ok"] += 1
        except Exception as e:
            _upload_text(container, out_blob, f"[SKIPPED] extraction error: {e}\n")
            summary["errors"] += 1

    meta["finished_at"] = _now_iso()
    meta_blob = f"{args.text_prefix.rstrip('/')}/metadata/seed_run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    container.get_blob_client(meta_blob).upload_blob(
        json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json; charset=utf-8"),
    )
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
