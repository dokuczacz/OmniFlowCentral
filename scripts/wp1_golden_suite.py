import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator
from unittest.mock import patch

from azure.core.exceptions import ResourceNotFoundError

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from OmniFlowCentral.shared.blob_ops import (
    delete_blob,
    get_filtered_data,
    list_blobs,
    read_blob,
    read_many_blobs,
    upload_blob,
)
from OmniFlowCentral.shared.data_ops import (
    add_new_data,
    dataset_search,
    manage_files,
    remove_data_entry,
    update_data_entry,
    upload_data_or_file,
)

class FakeBlob:
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size
        self.last_modified = datetime.utcnow()

class FakeDownloader:
    def __init__(self, data: bytes):
        self._data = data

    def readall(self) -> bytes:
        return self._data

class FakeBlobClient:
    def __init__(self, container: "FakeContainerClient", name: str):
        self.container = container
        self.name = name

    @property
    def url(self) -> str:
        return f"https://blob.fake/{self.name}"

    def download_blob(self) -> FakeDownloader:
        payload = self.container.blobs.get(self.name)
        if payload is None:
            raise ResourceNotFoundError("blob not found")
        return FakeDownloader(payload)

    def upload_blob(self, payload: bytes, overwrite: bool = False, **kwargs) -> None:
        self.container.blobs[self.name] = payload

    def delete_blob(self) -> None:
        if self.name not in self.container.blobs:
            raise ResourceNotFoundError("not found")
        del self.container.blobs[self.name]

    def start_copy_from_url(self, url: str) -> None:
        suffix = url.split("://", 1)[-1]
        source_name = suffix.split("/", 1)[-1] if "/" in suffix else suffix
        data = self.container.blobs.get(source_name)
        if data is None:
            raise ResourceNotFoundError("source missing")
        self.container.blobs[self.name] = data

class FakeContainerClient:
    def __init__(self):
        self.blobs: Dict[str, bytes] = {}

    def get_blob_client(self, name: str) -> FakeBlobClient:
        return FakeBlobClient(self, name)

    def list_blobs(self, name_starts_with: str = None, **_) -> Iterator[FakeBlob]:
        for name, data in list(self.blobs.items()):
            if name_starts_with and not name.startswith(name_starts_with):
                continue
            size = len(data) if isinstance(data, bytes) else len(str(data))
            yield FakeBlob(name, size)

container = FakeContainerClient()

with patch(
    "OmniFlowCentral.shared.blob_ops._get_container_client", lambda: container
), patch(
    "OmniFlowCentral.shared.data_ops._connect_container", lambda: container
):
    print("== WP1 Golden suite start ==")
    print("1) upload_blob")
    print("  ->", upload_blob("notes.json", "payload", "alice"))

    print("2) list_blobs")
    print("  ->", list_blobs("alice"))

    print("3) read_blob")
    print("  -> size", read_blob("alice", "notes.json")["size"])

    print("4) read_many_blobs")
    upload_blob("draft.md", "line1\nline2\n", "alice")
    print("  -> items", len(read_many_blobs("alice", ["notes.json", "draft.md"], tail_lines=1)["items"]))

    print("5) get_filtered_data")
    upload_data_or_file(
        "alice",
        {
            "target_blob_name": "records.json",
            "file_content": [{"status": "new"}, {"status": "done"}],
            "tags": ["dataset"],
        },
    )
    print("  -> filtered count", get_filtered_data("alice", "records.json", "status", "done")["count"])

    print("6) upload_data_or_file + add_new_data")
    upload_data_or_file(
        "alice",
        {
            "target_blob_name": "dataset.json",
            "file_content": {"name": "first"},
            "tags": ["search"],
            "summary": "initial",
        },
    )
    add_new_data(
        "alice",
        {"target_blob_name": "dataset.json", "new_entry": {"name": "second", "status": "ok"}},
    )

    print("7) update_data_entry")
    print(
        "  -> updated value",
        update_data_entry(
            "alice",
            {
                "target_blob_name": "dataset.json",
                "find_key": "name",
                "find_value": "second",
                "update_key": "status",
                "update_value": "done",
            },
        )["updated_value"],
    )

    print("8) remove_data_entry")
    print(
        "  ->", remove_data_entry(
            "alice",
            {
                "target_blob_name": "dataset.json",
                "find_key": "name",
                "find_value": "first",
                "update_key": "status",
                "update_value": "removed",
            },
        )["manifest_status"]
    )

    print("9) manage_files list/rename/delete")
    print("  -> list", manage_files("alice", {"operation": "list", "prefix": ""})["files"])
    manage_files(
        "alice",
        {
            "operation": "rename",
            "source_name": "dataset.json",
            "target_name": "dataset-renamed.json",
        },
    )
    manage_files("alice", {"operation": "delete", "source_name": "dataset-renamed.json"})

    print("10) dataset_search")
    search = dataset_search("alice", {"tags_any": ["search"], "limit": 5})
    print("  -> hits", len(search["hits"]), "total", search["total"])

    from OmniFlowCentral.shared.manifest_helper import load_manifest

    manifest_entries = load_manifest(container, "alice")["entries"]
    print("11) manifest entries", [entry["blob_name"] for entry in manifest_entries])
    print("== WP1 Golden suite end ==")
