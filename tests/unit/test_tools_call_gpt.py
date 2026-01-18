import json
from unittest.mock import patch

import OmniFlowCentral.tools_call_gpt as call_gpt


class _Req:
    def __init__(self, payload: dict):
        self.params = {}
        self._payload = payload

    def get_json(self):
        return self._payload


def test_tools_call_gpt_rejects_non_allowlisted_tool():
    req = _Req({"tool": "read_blob", "params": {"name": "x"}})
    resp = call_gpt.main(req)
    data = json.loads(resp.get_body().decode("utf-8"))
    assert data["status"] == "error"
    assert data["code"] == "INVALID_TOOL"


def test_tools_call_gpt_dispatches_query_dataset():
    req = _Req({"tool": "query_dataset", "params": {"dataset": "eli_acts", "limit": 1}})
    with patch("OmniFlowCentral.tools_call_gpt.query_dataset", return_value={"status": "success"}) as qd:
        resp = call_gpt.main(req)
    qd.assert_called_once()
    data = json.loads(resp.get_body().decode("utf-8"))
    assert data["status"] == "success"
    assert data["tool"] == "query_dataset"
    assert "result" in data

