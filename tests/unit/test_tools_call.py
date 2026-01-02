import json
from unittest.mock import MagicMock, patch

from OmniFlowCentral import tools_call


def test_tools_call_unsupported_tool(fake_req):
    req = fake_req(json_body={"tool": "no_such"})
    resp = tools_call.main(req)
    assert resp.status_code == 400
    body = json.loads(resp.get_body().decode('utf-8'))
    assert 'Unsupported tool' in body.get('error', '')


def test_tools_call_list_blobs_empty(fake_req):
    # mock ContainerClient to return no blobs
    fake_client = MagicMock()
    fake_client.list_blobs.return_value = []

    with patch('OmniFlowCentral.tools_call.ContainerClient') as CC:
        CC.from_connection_string.return_value = fake_client
        req = fake_req(json_body={"tool": "list_blobs"})
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode('utf-8'))
        assert 'blobs' in body
        assert isinstance(body['blobs'], list)
