from shared.request_contract import parse_request


class _Req:
    def __init__(self, body: dict):
        self.params = {}
        self._body = body

    def get_json(self):
        return self._body


def test_parse_request_unwraps_top_level_params_wrapper():
    req = _Req({"params": {"tool": "query_dataset", "params": {"dataset": "eli_acts"}}})
    out = parse_request(req)
    assert out["tool"] == "query_dataset"
    assert out["payload"]["params"]["dataset"] == "eli_acts"

