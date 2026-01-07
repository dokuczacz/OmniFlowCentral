import json
from unittest.mock import MagicMock, patch

from OmniFlowCentral import upload_blob, delete_blob


def test_upload_blob_success(fake_req):
    fake_blob = MagicMock()
    with patch('shared.blob_ops.ContainerClient') as CC:
        client = MagicMock()
        client.get_blob_client.return_value = fake_blob
        CC.from_connection_string.return_value = client

        req = fake_req(json_body={"name": "a.txt", "content": "hello"})
        resp = upload_blob.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode('utf-8'))
        assert body.get('result', {}).get('status') == 'uploaded'


def test_delete_blob_success(fake_req):
    fake_blob = MagicMock()
    with patch('shared.blob_ops.ContainerClient') as CC:
        client = MagicMock()
        client.get_blob_client.return_value = fake_blob
        CC.from_connection_string.return_value = client

        req = fake_req(json_body={"name": "a.txt"})
        resp = delete_blob.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode('utf-8'))
        assert body.get('result', {}).get('status') == 'deleted'
