import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from OmniFlowCentral.read_blob_file import main
from OmniFlowCentral.shared.blob_ops import ToolError


class DummyRequest:
    def __init__(self, params=None, headers=None, body=None):
        self.params = params or {}
        self.headers = headers or {}
        self._body = body or {}

    def get_json(self):
        return self._body


def _parse_response(resp):
    return json.loads(resp.get_body().decode("utf-8"))


def test_read_blob_success(monkeypatch):
    def fake_read_blob(user_id, name):
        return {"data": {"value": "ok"}, "content_type": "json", "file_name": name}

    monkeypatch.setattr("OmniFlowCentral.read_blob_file.read_blob", fake_read_blob)
    req = DummyRequest(params={"file_name": "notes.json"}, headers={"X-User-Id": "alice"})
    resp = main(req)
    payload = _parse_response(resp)
    assert resp.status_code == 200
    assert payload["status"] == "success"
    assert payload["result"]["data"] == {"value": "ok"}


def test_read_blob_missing_parameter():
    req = DummyRequest(params={}, headers={"X-User-Id": "alice"})
    resp = main(req)
    payload = _parse_response(resp)
    assert resp.status_code == 400
    assert payload["code"] == "MISSING_PARAM"


def test_read_blob_not_found(monkeypatch):
    def fake_read_blob(user_id, name):
        raise ToolError("MISSING_PARAM", "File missing", status=404)

    monkeypatch.setattr("OmniFlowCentral.read_blob_file.read_blob", fake_read_blob)
    req = DummyRequest(params={"file_name": "missing.json"}, headers={"X-User-Id": "alice"})
    resp = main(req)
    payload = _parse_response(resp)
    assert resp.status_code == 404
    assert payload["code"] == "MISSING_PARAM"
