import json
from unittest.mock import patch

import pytest

from shared.blob_ops import ToolError
from OmniFlowCentral.shared.data_ops import query_dataset


class _StubDownload:
    def __init__(self, payload: bytes):
        self._payload = payload

    def readall(self) -> bytes:
        return self._payload


class _StubBlobClient:
    def __init__(self, payload: bytes):
        self._payload = payload

    def download_blob(self):
        return _StubDownload(self._payload)


class _StubContainer:
    def __init__(self, blobs: dict[str, bytes]):
        self._blobs = blobs

    def get_blob_client(self, name: str):
        return _StubBlobClient(self._blobs[name])


def test_query_dataset_eli_matches_display_address():
    index_path = "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl"    
    line = json.dumps(
        {
            "ELI": "DU/2025/1882",
            "displayAddress": "Dz.U. 2025 poz. 1882",
            "publisher": "DU",
            "year": 2025,
            "pos": 1882,
            "title": "Ustawa testowa",
            "status": "obowiązujący",
        },
        ensure_ascii=False,
    )
    blobs = {index_path: (line + "\n").encode("utf-8")}

    with patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs)):
        resp = query_dataset({"dataset": "eli_acts", "q": "Dz.U. 2025 poz. 1882", "limit": 5})

    assert resp["status"] == "success"
    assert resp["total_returned"] == 1
    assert resp["hits"][0]["ELI"] == "DU/2025/1882"


def test_query_dataset_eli_matches_display_address_alias_dz_ust():
    index_path = "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl"
    line = json.dumps(
        {
            "ELI": "DU/2025/1882",
            "displayAddress": "Dz.U. 2025 poz. 1882",
            "publisher": "DU",
            "year": 2025,
            "pos": 1882,
            "title": "Ustawa testowa",
            "status": "obowiązujący",
        },
        ensure_ascii=False,
    )
    blobs = {index_path: (line + "\n").encode("utf-8")}

    with patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs)):
        resp = query_dataset({"dataset": "eli_acts", "q": "dz ust 2025 poz 1882", "limit": 5})

    assert resp["status"] == "success"
    assert resp["total_returned"] == 1


def test_query_dataset_eli_matches_eli_id_alias_dzu_slashes():
    index_path = "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl"
    line = json.dumps(
        {
            "ELI": "DU/2025/1882",
            "displayAddress": "Dz.U. 2025 poz. 1882",
            "publisher": "DU",
            "year": 2025,
            "pos": 1882,
            "title": "Ustawa testowa",
            "status": "obowiązujący",
        },
        ensure_ascii=False,
    )
    blobs = {index_path: (line + "\n").encode("utf-8")}

    with patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs)):
        resp = query_dataset({"dataset": "eli_acts", "q": "dz.u. 2025/1882", "limit": 5})

    assert resp["status"] == "success"
    assert resp["total_returned"] == 1


def test_query_dataset_eli_or_query_matches_display_address():
    index_path = "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl"    
    line = json.dumps(
        {
            "ELI": "DU/2025/1882",
            "displayAddress": "Dz.U. 2025 poz. 1882",
            "publisher": "DU",
            "year": 2025,
            "pos": 1882,
            "title": "Ustawa testowa",
            "status": "obowiązujący",
        },
        ensure_ascii=False,
    )
    blobs = {index_path: (line + "\n").encode("utf-8")}

    with patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs)):
        resp = query_dataset({"dataset": "eli_acts", "q": "nope OR Dz.U. 2025 poz. 1882", "limit": 5})

    assert resp["status"] == "success"
    assert resp["total_returned"] == 1


def test_query_dataset_saos_and_query_matches_case_number_and_court():
    index_path = "users/public/datasets/saos/judgments/index/judgments_index.jsonl"
    index_line = json.dumps(
        {
            "caseNumber": "VIII Kop 254/09",
            "court": "Sąd Okręgowy w Warszawie",
            "courtType": "common",
            "pageId": "page_00001",
            "recordIndex": 0,
            "summary": "test",
        },
        ensure_ascii=False,
    )
    blobs = {index_path: (index_line + "\n").encode("utf-8")}

    with patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs)):
        resp = query_dataset({"dataset": "saos_judgments", "q": "kop 254/09 AND warszawie", "limit": 5})

    assert resp["status"] == "success"
    assert resp["total_returned"] == 1


def test_query_dataset_eli_lookup_by_page_id_alias():
    index_path = "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl"
    line = json.dumps(
        {"ELI": "DU/2003/2065", "publisher": "DU", "year": 2003, "pos": 2065, "title": "Rozporządzenie"},
        ensure_ascii=False,
    )
    blobs = {index_path: (line + "\n").encode("utf-8")}

    with patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs)):
        resp = query_dataset({"dataset": "eli_acts", "pageId": "DU/2003/2065", "fetch_content": False})

    assert resp["status"] == "success"
    assert resp["total_returned"] == 1
    assert resp["hits"][0]["ELI"] == "DU/2003/2065"
    assert resp["hits"][0]["pageId"] == "DU/2003/2065"
    assert resp["hits"][0]["recordIndex"] == 2065


def test_query_dataset_saos_lookup_by_page_and_record_index_fetches_content():  
    index_path = "users/public/datasets/saos/judgments/index/judgments_index.jsonl"
    page_path = "users/public/datasets/saos/judgments/pages/page_00001.json"
    index_line = json.dumps(
        {
            "caseNumber": "I ACa 1/20",
            "court": "Sąd Apelacyjny w Gdańsku",
            "courtType": "common",
            "pageId": "page_00001",
            "recordIndex": 0,
            "summary": "test",
        },
        ensure_ascii=False,
    )
    page_payload = json.dumps([{"full": "content"}], ensure_ascii=False).encode("utf-8")
    blobs = {
        index_path: (index_line + "\n").encode("utf-8"),
        page_path: page_payload,
    }

    with patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs)):
        resp = query_dataset(
            {
                "dataset": "saos_judgments",
                "pageId": "page_00001",
                "recordIndex": "0",
                "fetch_content": True,
                "limit": 5,
            }
        )

    assert resp["status"] == "success"
    assert resp["total_returned"] == 1
    assert resp["hits"][0]["_fullContent"] == {"full": "content"}


def test_query_dataset_saos_sanitizes_invalid_date():
    index_path = "users/public/datasets/saos/judgments/index/judgments_index.jsonl"
    index_line = json.dumps(
        {
            "caseNumber": "I ACa 1/20",
            "court": "Sąd Apelacyjny w Gdańsku",
            "courtType": "common",
            "pageId": "page_00001",
            "recordIndex": 0,
            "judgmentDate": "0208-03-14",
            "summary": "test",
        },
        ensure_ascii=False,
    )
    blobs = {index_path: (index_line + "\n").encode("utf-8")}

    with patch("OmniFlowCentral.shared.data_ops._connect_container", return_value=_StubContainer(blobs)):
        resp = query_dataset({"dataset": "saos_judgments", "q": "test", "limit": 5})

    assert resp["status"] == "success"
    assert resp["total_returned"] == 1
    assert resp["hits"][0].get("judgmentDate") is None


def test_query_dataset_saos_record_index_requires_page_id():
    with pytest.raises(ToolError) as exc:
        query_dataset({"dataset": "saos_judgments", "recordIndex": 0})
    assert exc.value.code == "VALIDATION_FAILED"
