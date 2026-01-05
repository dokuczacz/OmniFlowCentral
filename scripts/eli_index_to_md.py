"""
Create a Markdown export summarizing the stored ELI index.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from azure.storage.blob import ContainerClient

from OmniFlowCentral.shared.config import AzureConfig


def _run_meta_prefix(blob_prefix: str, user_id: str) -> str:
    return f"users/{user_id}/{blob_prefix.rstrip('/')}/runs/"


def _latest_run_blob(container: ContainerClient, prefix: str) -> Tuple[str, Dict[str, Any]]:
    blobs = sorted(blob.name for blob in container.list_blobs(name_starts_with=prefix))
    if not blobs:
        raise ValueError(f"No run metadata found under {prefix!r}")
    latest = blobs[-1]
    payload = container.get_blob_client(latest).download_blob().readall()
    return latest, json.loads(payload)


def _resolve_index_blob(run_meta: Dict[str, Any], user_id: str, blob_prefix: str) -> str:
    blob_ref = run_meta.get("checksum", {}).get("items_jsonl", {}).get("blob_name")
    if blob_ref:
        return blob_ref if blob_ref.startswith("users/") else f"users/{user_id}/{blob_ref}"
    return f"users/{user_id}/{blob_prefix.rstrip('/')}/index/acts_inforce_1.jsonl"


def _sample_entries(container: ContainerClient, blob_name: str, limit: int) -> List[Dict[str, Any]]:
    blob_client = container.get_blob_client(blob_name)
    streamer = blob_client.download_blob()
    buffer = ""
    samples: List[Dict[str, Any]] = []
    for chunk in streamer.chunks():
        text = chunk.decode("utf-8")
        buffer += text
        while "\n" in buffer and len(samples) < limit:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            samples.append(json.loads(line))
        if len(samples) >= limit:
            break
    return samples


def _render_markdown(output: Path, run_meta: Dict[str, Any], samples: List[Dict[str, Any]], index_blob: str) -> None:
    lines = [
        "# ELI acts export (inForce=1)",
        "",
        f"- generated at: {run_meta.get('finished_at', '')}",
        f"- run id: {run_meta.get('run_id', '')}",
        f"- index blob: `{index_blob}`",
        "",
        "## Sample records",
        "",
        "| ELI | Year | Status | Announcement | Change |",
        "| --- | ---- | ------ | ------------ | ------ |",
    ]
    for item in samples:
        title = (item.get("title") or "").replace("|", "\\|")
        lines.append(
            "| {ELI} | {year} | {status} | {announcement} | {change} |".format(
                ELI=item.get("ELI", ""),
                year=item.get("year") or "",
                status=item.get("status", ""),
                announcement=item.get("announcementDate", ""),
                change=item.get("changeDate", ""),
            )
        )
    lines += [
        "",
        "## Run metadata (raw)",
        "",
        "```json",
        json.dumps(run_meta, ensure_ascii=False, indent=2),
        "```",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export ELI JSONL index as Markdown.")
    parser.add_argument("--output", type=Path, default=Path("docs/eli_acts_export.md"), help="Markdown output path.")
    parser.add_argument("--user-id", default="public", help="Namespace under users/ (default: public).")
    parser.add_argument("--blob-prefix", default="datasets/eli_acts", help="Storage prefix for the dataset.")
    parser.add_argument("--sample-size", type=int, default=10, help="Number of rows to materialize (default: 10).")
    args = parser.parse_args()

    container = ContainerClient.from_connection_string(AzureConfig.CONNECTION_STRING, AzureConfig.CONTAINER_NAME)
    run_prefix = _run_meta_prefix(args.blob_prefix, args.user_id)
    latest_blob, run_meta = _latest_run_blob(container, run_prefix)
    index_blob = _resolve_index_blob(run_meta, args.user_id, args.blob_prefix)
    samples = _sample_entries(container, index_blob, args.sample_size)
    _render_markdown(args.output, run_meta, samples, index_blob)
    logging.info("Wrote Markdown export to %s", args.output)
    return 0


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    raise SystemExit(main())
