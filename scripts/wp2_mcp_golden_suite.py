import argparse
import contextlib
import json
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Iterator, Optional
from unittest.mock import patch

from azure.core.exceptions import ResourceNotFoundError

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_APP_ROOT = _REPO_ROOT / "OmniFlowCentral"
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from OmniFlowCentral.mcp_app.adapter import (  # noqa: E402
    run_dataset_search,
    run_fetch,
    run_query_dataset,
    run_search,
)
from OmniFlowCentral.mcp_app.tool_matrix import build_tool_migration_matrix  # noqa: E402

TEST_USER = "wp2_user"
ELI_PAGE_ID = "DU/2025/1882"
ELI_INDEX_PATH = "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl"
ELI_TEXT_PATH = f"users/public/datasets/eli_acts/text/{ELI_PAGE_ID}.txt"


class FakeBlob:
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size


class FakeDownloader:
    def __init__(self, data: bytes):
        self._data = data

    def readall(self) -> bytes:
        return self._data


class FakeBlobClient:
    def __init__(self, container: "FakeContainer", name: str):
        self.container = container
        self.name = name

    def download_blob(self) -> FakeDownloader:
        payload = self.container.blobs.get(self.name)
        if payload is None:
            raise ResourceNotFoundError("blob not found")
        return FakeDownloader(payload)

    def upload_blob(self, payload: bytes, overwrite: bool = False, **kwargs) -> None:
        self.container.blobs[self.name] = payload


class FakeContainer:
    def __init__(self):
        self.blobs: Dict[str, bytes] = {}

    def get_blob_client(self, name: str) -> FakeBlobClient:
        return FakeBlobClient(self, name)

    def list_blobs(self, name_starts_with: Optional[str] = None, **_) -> Iterator[FakeBlob]:
        for name, data in list(self.blobs.items()):
            if name_starts_with and not name.startswith(name_starts_with):
                continue
            yield FakeBlob(name, len(data))


def _seed_data(container: FakeContainer) -> None:
    index_record = {
        "ELI": ELI_PAGE_ID,
        "pos": 0,
        "title": "Ustawa testowa o ruchu drogowym",
        "displayAddress": "Dz.U. 2025 poz. 1882",
        "publisher": "DU",
        "status": "akt_obowiazujacy",
        "year": 2025,
    }
    container.blobs[ELI_INDEX_PATH] = (json.dumps(index_record, ensure_ascii=False) + "\n").encode("utf-8")
    container.blobs[ELI_TEXT_PATH] = "Pełna treść aktu testowego dla MCP golden suite.".encode("utf-8")

    manifest = {
        "manifest_version": 1,
        "updated_at": "2026-02-23T00:00:00Z",
        "entries": [
            {
                "blob_name": ELI_INDEX_PATH,
                "display_name": "ELI acts index",
                "summary": "Test index for WP2 MCP golden suite",
                "tags": ["eli", "acts", "search"],
                "category": "dataset",
                "source": "wp2_golden",
                "size": len(container.blobs[ELI_INDEX_PATH]),
                "content_type": "application/x-ndjson",
                "updated_at": "2026-02-23T00:00:00Z",
                "created_at": "2026-02-23T00:00:00Z",
                "manifest_tags": ["golden"],
                "metadata": {"dataset": "eli_acts"},
            }
        ],
    }
    container.blobs[f"manifests/{TEST_USER}/manifest.json"] = json.dumps(
        manifest, ensure_ascii=False
    ).encode("utf-8")


def _as_dict(payload):
    if isinstance(payload, dict):
        return payload
    raise AssertionError(f"Expected dict payload, got {type(payload)!r}")


def _parse_text_payload(result) -> Dict[str, object]:
    if not result.content:
        raise AssertionError("Missing tool text content")
    text_item = result.content[0]
    text_value = getattr(text_item, "text", "")
    if not text_value:
        raise AssertionError("Empty tool text content")
    return _as_dict(json.loads(text_value))


def run_suite(container: FakeContainer) -> None:
    print("== WP2 MCP Golden suite start ==")
    print("1) query_dataset (eli_acts)")
    query_result = run_query_dataset({"dataset": "eli_acts", "q": "ruchu", "limit": 5})
    assert not query_result.isError, query_result
    query_structured = _as_dict(query_result.structuredContent)
    assert query_structured.get("status") == "success"
    assert query_structured.get("dataset") == "eli_acts"
    assert query_structured.get("total_returned", 0) >= 1
    print("  -> ok")

    print("2) dataset_search (manifest discovery)")
    ds_result = run_dataset_search(
        {
            "user_id": TEST_USER,
            "q": "ELI",
            "tags_any": ["search"],
            "limit": 5,
        }
    )
    assert not ds_result.isError, ds_result
    ds_structured = _as_dict(ds_result.structuredContent)
    assert ds_structured.get("status") == "success"
    assert ds_structured.get("user_id") == TEST_USER
    assert len(ds_structured.get("hits") or []) >= 1
    print("  -> ok")

    print("3) search wrapper")
    search_result = run_search({"query": "ruchu", "dataset": "eli_acts", "limit": 5})
    assert not search_result.isError, search_result
    search_payload = _parse_text_payload(search_result)
    results = search_payload.get("results") or []
    assert isinstance(results, list)
    assert len(results) >= 1
    first_result = _as_dict(results[0])
    assert first_result.get("id")
    assert first_result.get("url")
    print("  -> ok")

    print("4) fetch wrapper")
    fetch_id = first_result["id"]
    fetch_result = run_fetch({"id": str(fetch_id), "dataset": "eli_acts"})
    assert not fetch_result.isError, fetch_result
    fetch_payload = _parse_text_payload(fetch_result)
    assert fetch_payload.get("id") == fetch_id
    assert "treść aktu" in str(fetch_payload.get("text") or "").lower()
    metadata = fetch_payload.get("metadata")
    assert isinstance(metadata, dict)
    assert metadata.get("dataset") == "eli_acts"
    print("  -> ok")

    print("5) migration_matrix")
    tools = build_tool_migration_matrix()
    assert isinstance(tools, list)
    assert any(item.tool == "query_dataset" for item in tools)
    print("  -> ok")

    print("== WP2 MCP Golden suite: SUCCESS ==")


def _run_inner() -> None:
    fake_container = FakeContainer()
    _seed_data(fake_container)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("OmniFlowCentral.shared.blob_ops._get_container_client", lambda: fake_container)
        )
        stack.enter_context(
            patch("shared.blob_ops._get_container_client", lambda: fake_container)
        )
        stack.enter_context(
            patch("OmniFlowCentral.shared.data_ops._connect_container", lambda: fake_container)
        )
        stack.enter_context(
            patch("shared.data_ops._connect_container", lambda: fake_container)
        )
        run_suite(fake_container)


def run(timeout_seconds: float = 30.0) -> None:
    if timeout_seconds <= 0:
        _run_inner()
        return

    start = time.monotonic()
    errors = []

    def _target() -> None:
        try:
            _run_inner()
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    worker.join(timeout_seconds)

    if worker.is_alive():
        elapsed = time.monotonic() - start
        raise TimeoutError(f"WP2 MCP Golden suite timed out after {elapsed:.1f}s.")
    if errors:
        raise errors[0]

    elapsed = time.monotonic() - start
    print(f"== WP2 MCP Golden suite completed in {elapsed:.2f}s ==")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WP2 MCP golden suite.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="Maximum suite runtime in seconds (0 disables timeout).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(timeout_seconds=args.timeout_seconds)
