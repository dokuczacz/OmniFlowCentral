import json

import OmniFlowCentral.tools_capabilities_gpt as tc


def test_tools_capabilities_gpt_returns_minimal_list():
    # tools_capabilities_gpt.main ignores the req content; pass None-like object
    class R: pass

    resp = tc.main(R())
    body = resp.get_body().decode("utf-8")
    data = json.loads(body)
    assert "capabilities" in data
    names = [c.get("name") for c in data["capabilities"]]
    assert set(names) == {"query_dataset", "dataset_search"}

