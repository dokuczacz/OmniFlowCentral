#!/usr/bin/env python3
"""
Mirror SAOS artifacts inside the same Azure container:
  datasets/saos/...  ->  users/public/datasets/saos/...

Why: query_dataset currently reads SAOS from datasets/saos/... but Custom GPT
expects public datasets under users/public/...

This script copies blobs (streaming) and is restartable.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from azure.storage.blob import BlobServiceClient, ContentSettings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_type(name: str) -> str:
    n = name.lower()
    if n.endswith(".json") or n.endswith(".jsonl"):
        return "application/json; charset=utf-8"
    if n.endswith(".txt"):
        return "text/plain; charset=utf-8"
    return "application/octet-stream"


@dataclass(frozen=True)
class MirrorSpec:
    src_prefix: str
    dst_prefix: str


DEFAULT_SPEC = MirrorSpec(
    src_prefix="datasets/saos/",
    dst_prefix="users/public/datasets/saos/",
)


def _iter_blobs(container, prefix: str, *, max_items: int) -> Iterator[Tuple[str, int]]:
    for i, b in enumerate(container.list_blobs(name_starts_with=prefix)):
        if i >= max_items:
            break
        yield b.name, int(getattr(b, "size", 0) or 0)


def _dst_name(spec: MirrorSpec, src_name: str) -> str:
    return spec.dst_prefix + src_name[len(spec.src_prefix) :]


def _dst_exists_same_size(container, name: str, size: int) -> bool:
    try:
        props = container.get_blob_client(name).get_blob_properties()
        return int(getattr(props, "size", 0) or 0) == int(size)
    except Exception:
        return False


def _copy_stream(container, src_name: str, dst_name: str) -> None:
    downloader = container.get_blob_client(src_name).download_blob(max_concurrency=4)
    container.get_blob_client(dst_name).upload_blob(
        downloader.chunks(),
        overwrite=True,
        content_settings=ContentSettings(content_type=_content_type(dst_name)),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Mirror SAOS blobs from datasets/saos to users/public/datasets/saos.")
    ap.add_argument(
        "--connection-string",
        default=os.environ.get("AZURE_STORAGE_CONNECTION_STRING", ""),
        help="Azure Storage connection string (env: AZURE_STORAGE_CONNECTION_STRING).",
    )
    ap.add_argument("--container-name", default="omniflowcentralcustomgpt")
    ap.add_argument("--src-prefix", default=DEFAULT_SPEC.src_prefix)
    ap.add_argument("--dst-prefix", default=DEFAULT_SPEC.dst_prefix)
    ap.add_argument("--max-items", type=int, default=5_000_000)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--skip-existing", action="store_true", help="Skip if dst exists with same size.")
    ap.add_argument("--progress-every", type=int, default=2000)
    ap.add_argument("--progress-file", default="tmp/saos_mirror_progress.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cs = (args.connection_string or "").strip()
    if not cs:
        raise SystemExit("Missing --connection-string / AZURE_STORAGE_CONNECTION_STRING")

    spec = MirrorSpec(src_prefix=args.src_prefix, dst_prefix=args.dst_prefix)
    if not spec.src_prefix.endswith("/"):
        raise SystemExit("--src-prefix must end with /")
    if not spec.dst_prefix.endswith("/"):
        raise SystemExit("--dst-prefix must end with /")

    cont = BlobServiceClient.from_connection_string(cs).get_container_client(args.container_name)

    work: List[Tuple[str, str, int]] = []
    for src_name, size in _iter_blobs(cont, spec.src_prefix, max_items=int(args.max_items)):
        dst_name = _dst_name(spec, src_name)
        work.append((src_name, dst_name, size))

    t0 = time.time()
    counters: Dict[str, int] = {"copied": 0, "skipped": 0, "errors": 0}
    bytes_copied = 0

    def write_progress(done: int, *, finished: bool) -> None:
        if not args.progress_file:
            return
        try:
            os.makedirs(os.path.dirname(args.progress_file) or ".", exist_ok=True)
            elapsed = max(0.001, time.time() - t0)
            payload = {
                "tool": "saos_mirror_to_public",
                "started_at": datetime.fromtimestamp(t0, tz=timezone.utc).isoformat(),
                "updated_at": _now_iso(),
                "finished": bool(finished),
                "container": args.container_name,
                "src_prefix": spec.src_prefix,
                "dst_prefix": spec.dst_prefix,
                "skip_existing": bool(args.skip_existing),
                "dry_run": bool(args.dry_run),
                "workers": int(args.workers),
                "done": int(done),
                "total": int(len(work)),
                "bytes_copied": int(bytes_copied),
                "mbps": round((bytes_copied / elapsed) / (1024 * 1024), 2),
                "counters": dict(counters),
            }
            with open(args.progress_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            return

    def do_one(item: Tuple[str, str, int]) -> Tuple[bool, int, Optional[str]]:
        src_name, dst_name, size = item
        if args.dry_run:
            return False, 0, None
        if args.skip_existing and _dst_exists_same_size(cont, dst_name, size):
            return False, 0, None
        try:
            _copy_stream(cont, src_name, dst_name)
            return True, size, None
        except Exception as e:
            return False, 0, str(e)

    write_progress(0, finished=False)
    with ThreadPoolExecutor(max_workers=int(args.workers)) as ex:
        futs = [ex.submit(do_one, item) for item in work]
        for i, fut in enumerate(as_completed(futs), 1):
            copied, size, err = fut.result()
            if copied:
                counters["copied"] += 1
                bytes_copied += int(size)
            else:
                counters["skipped"] += 1
            if err:
                counters["errors"] += 1
            if int(args.progress_every) > 0 and i % int(args.progress_every) == 0:
                elapsed = max(0.001, time.time() - t0)
                print(
                    {
                        "tool": "saos_mirror_to_public",
                        "updated_at": _now_iso(),
                        "done": i,
                        "total": len(work),
                        "bytes_copied": bytes_copied,
                        "mbps": round((bytes_copied / elapsed) / (1024 * 1024), 2),
                        "counters": dict(counters),
                    },
                    flush=True,
                )
                write_progress(i, finished=False)

    write_progress(len(work), finished=True)
    print(
        {
            "tool": "saos_mirror_to_public",
            "finished_at": _now_iso(),
            "items_total": len(work),
            "bytes_copied": bytes_copied,
            "counters": dict(counters),
        },
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

