import json

import OmniFlowCentral.tools_capabilities as tc
from OmniFlowCentral.shared.tool_specs import TOOL_SPECS


def test_tools_capabilities_returns_list():
    # tools_capabilities.main ignores the req content; pass None-like object
    class R: pass

    resp = tc.main(R())
    body = resp.get_body().decode('utf-8')
    data = json.loads(body)
    assert 'capabilities' in data
    names = [c.get('name') for c in data['capabilities']]
    assert 'list_blobs' in names
    assert set(names) == set(TOOL_SPECS.keys())
