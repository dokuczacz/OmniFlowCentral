import json
import contextlib
from unittest.mock import patch

from azure.core.exceptions import ResourceNotFoundError

from OmniFlowCentral.mcp_app.adapter import run_fetch, run_search


class _StubDownload:
    def __init__(self, payload: bytes):
        self._payload = payload

    def readall(self) -> bytes:
        return self._payload


class _StubBlobClient:
    def __init__(self, blobs: dict[str, bytes], name: str):
        self._blobs = blobs
        self._name = name

    def download_blob(self):
        if self._name not in self._blobs:
            raise ResourceNotFoundError("blob not found")
        return _StubDownload(self._blobs[self._name])


class _StubContainer:
    def __init__(self, blobs: dict[str, bytes]):
        self._blobs = blobs

    def get_blob_client(self, name: str):
        return _StubBlobClient(self._blobs, name)


def _seed_eli_payload() -> dict[str, bytes]:
    index_path = "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl"
    text_path = "users/public/datasets/eli_acts/text/DU/2025/1882.txt"
    line = json.dumps(
        {
            "ELI": "DU/2025/1882",
            "displayAddress": "Dz.U. 2025 poz. 1882",
            "publisher": "DU",
            "year": 2025,
            "pos": 1882,
            "title": "Ustawa testowa",
            "status": "obowiązujący",
            "pageId": "DU/2025/1882",
            "recordIndex": 1882,
        },
        ensure_ascii=False,
    )
    return {
        index_path: (line + "\n").encode("utf-8"),
        text_path: "Pełna treść aktu testowego.".encode("utf-8"),
    }


def _parse_text_json(result):
    assert result.content, "Tool result should include text content"
    text = getattr(result.content[0], "text", "")
    assert text, "Tool result text should not be empty"
    payload = json.loads(text)
    assert isinstance(payload, dict)
    return payload


def test_mcp_search_contract_shape_and_citation_url():
    blobs = _seed_eli_payload()
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs))
        )
        stack.enter_context(
            patch("shared.data_ops._connect_container", return_value=_StubContainer(blobs))
        )
        result = run_search({"query": "ustawa", "dataset": "eli_acts", "limit": 5})

    assert result.isError is False
    payload = _parse_text_json(result)

    results = payload.get("results")
    assert isinstance(results, list)
    assert len(results) >= 1

    first = results[0]
    assert isinstance(first, dict)
    assert isinstance(first.get("id"), str) and first["id"].strip()
    assert isinstance(first.get("title"), str) and first["title"].strip()
    assert isinstance(first.get("url"), str) and first["url"].strip()
    assert first["url"].startswith("https://")


def test_mcp_fetch_contract_shape_for_eli_id():
    blobs = _seed_eli_payload()
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs))
        )
        stack.enter_context(
            patch("shared.data_ops._connect_container", return_value=_StubContainer(blobs))
        )
        result = run_fetch({"id": "eli_acts:DU/2025/1882:1882", "dataset": "eli_acts"})

    assert result.isError is False
    payload = _parse_text_json(result)

    assert payload.get("id") == "eli_acts:DU/2025/1882:1882"
    assert isinstance(payload.get("title"), str) and payload["title"].strip()
    assert isinstance(payload.get("text"), str) and payload["text"].strip()
    assert isinstance(payload.get("url"), str) and payload["url"].startswith("https://")

    metadata = payload.get("metadata")
    assert isinstance(metadata, dict)
    assert metadata.get("dataset") == "eli_acts"
    assert metadata.get("pageId") == "DU/2025/1882"


def test_mcp_fetch_missing_id_returns_error_contract():
    result = run_fetch({"dataset": "eli_acts"})
    assert result.isError is True
    assert isinstance(result.structuredContent, dict)
    error = result.structuredContent.get("error")
    assert isinstance(error, dict)
    assert error.get("code") == "MISSING_PARAM"
