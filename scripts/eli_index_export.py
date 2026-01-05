"""
Download existing ELI pages from Azure blob storage and write a flat JSONL index.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

_REPO_ROOT = Path(__file__).resolve().parents[1]
_APP2_ROOT = _REPO_ROOT / "OmniFlowCentral"
if str(_APP2_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP2_ROOT))

from azure.storage.blob import ContainerClient

from OmniFlowCentral.shared.config import AzureConfig


def _list_page_blobs(container: ContainerClient, prefix: str) -> List[str]:
    return sorted(blob.name for blob in container.list_blobs(name_starts_with=prefix))


def _download_page(container: ContainerClient, blob_name: str) -> dict:
    blob_client = container.get_blob_client(blob_name)
    payload = blob_client.download_blob().readall()
    return json.loads(payload)


def extract_jsonl(*, container: ContainerClient, prefix: str, output: Path, batch_size: int) -> int:
    pages = _list_page_blobs(container, prefix)
    if not pages:
        raise ValueError(f"No page blobs found under prefix {prefix!r}.")

    total_lines = 0
    with output.open("w", encoding="utf-8") as fh:
        for idx, blob_name in enumerate(pages, 1):
            page = _download_page(container, blob_name)
            items = page.get("items") or []
            for item in items:
                fh.write(json.dumps(item, ensure_ascii=False))
                fh.write("\n")
            total_lines += len(items)
            if batch_size and idx % batch_size == 0:
                logging.info("Exported %s/%s pages (%s records)", idx, len(pages), total_lines)
    return total_lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Export ELI act pages to JSONL.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/eli_acts_index.jsonl"),
        help="Destination JSONL file (default: data/eli_acts_index.jsonl).",
    )
    parser.add_argument(
        "--user-id",
        default="public",
        help="Namespace used under users/ (default: public).",
    )
    parser.add_argument(
        "--blob-prefix",
        default="datasets/eli_acts",
        help="Prefix under the namespace where pages live (default: datasets/eli_acts).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Log progress every N pages (default: 10).",
    )
    args = parser.parse_args()

    container = ContainerClient.from_connection_string(
        AzureConfig.CONNECTION_STRING, AzureConfig.CONTAINER_NAME
    )
    prefix = f"users/{args.user_id}/{args.blob_prefix.rstrip('/')}/pages/"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    total = extract_jsonl(container=container, prefix=prefix, output=args.output, batch_size=args.batch_size)
    logging.info("Finished writing %s records to %s", total, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
