from OmniFlowCentral.shared import request_contract


class FakeReq:
    def __init__(self, params=None, json_body=None):
        self.params = params or {}
        self._json = json_body

    def get_json(self):
        if self._json is None:
            raise ValueError("No JSON")
        return self._json


def test_parse_prefers_query_over_body():
    req = FakeReq(params={"tool": "from_query"}, json_body={"tool": "from_body", "x": 1})
    out = request_contract.parse_request(req)
    assert out["tool"] == "from_query"
    assert out["payload"].get("x") == 1


def test_parse_handles_missing_json():
    req = FakeReq(params={"tool": "q"}, json_body=None)
    out = request_contract.parse_request(req)
    assert out["tool"] == "q"
    assert isinstance(out["payload"], dict)
