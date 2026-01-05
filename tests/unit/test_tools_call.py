import json
from unittest.mock import patch

from OmniFlowCentral import tools_call
from OmniFlowCentral.shared.tool_specs import TOOL_SPECS


def test_tools_call_unsupported_tool(fake_req):
    req = fake_req(json_body={"tool": "no_such"})
    resp = tools_call.main(req)
    assert resp.status_code == 400
    body = json.loads(resp.get_body().decode('utf-8'))
    assert body["code"] == "INVALID_TOOL"
    assert "Unsupported tool" in body.get("message", "")


def test_tools_call_list_blobs_empty(fake_req):
    with patch("OmniFlowCentral.tools_call.list_blobs", return_value=[]) as mock_list:
        req = fake_req(json_body={"tool": "list_blobs", "params": {"prefix": "notes"}})
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["status"] == "success"
        assert body["result"]["items"] == []
        mock_list.assert_called_once()


def test_tools_call_list_blobs_user_header(fake_req):
    with patch("OmniFlowCentral.tools_call.list_blobs", return_value=[]) as mock_list:
        req = fake_req(
            json_body={"tool": "list_blobs", "params": {}, "trace_id": "trace-123"},
            headers={"X-User-Id": "bob"},
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["trace_id"] == "trace-123"
        mock_list.assert_called_once()
        assert mock_list.call_args.kwargs["user_id"] == "bob"


def test_tools_call_list_blobs_default_user(fake_req):
    with patch("OmniFlowCentral.tools_call.list_blobs", return_value=[]) as mock_list:
        req = fake_req(json_body={"tool": "list_blobs", "params": {}}, headers={})
        resp = tools_call.main(req)
        assert resp.status_code == 200
        mock_list.assert_called_once()
        assert mock_list.call_args.kwargs["user_id"] == "default"


def test_tools_call_read_blob_file_alias(fake_req):
    expected = {"file_name": "notes.json", "data": {"foo": "bar"}}
    with patch("OmniFlowCentral.tools_call.read_blob", return_value=expected) as mock_read:
        req = fake_req(
            json_body={"tool": "read_blob_file", "params": {"file_name": "notes.json"}},
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == expected
        mock_read.assert_called_once()
        call_kwargs = mock_read.call_args.kwargs
        assert call_kwargs["user_id"] == "alice"
        assert call_kwargs["name"] == "notes.json"


def test_tools_call_read_many_blobs(fake_req):
    expected = {"items": [], "count": 0, "errors": 0, "total_bytes": 0}
    with patch("OmniFlowCentral.tools_call.read_many_blobs", return_value=expected) as mock_read:
        req = fake_req(
            json_body={
                "tool": "read_many_blobs",
                "params": {"files": ["notes.json"], "tail_lines": 2, "parse_json": False},
            }
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == expected
        mock_read.assert_called_once()
        call_kwargs = mock_read.call_args.kwargs
        assert call_kwargs["user_id"] == "alice"
        assert call_kwargs["files"] == ["notes.json"]
        assert call_kwargs["tail_lines"] == 2
        assert call_kwargs["parse_json"] is False


def test_tools_call_handlers_match_tool_specs():
    assert set(tools_call.TOOL_HANDLERS.keys()) == set(TOOL_SPECS.keys())


def test_tools_call_get_filtered_data(fake_req):
    expected = {"status": "success", "file": "notes.json"}
    with patch("OmniFlowCentral.tools_call.get_filtered_data", return_value=expected) as mock_filter:
        req = fake_req(
            json_body={
                "tool": "get_filtered_data",
                "params": {"target_blob_name": "notes.json", "filter_key": "status", "filter_value": "ok"},
            }
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == expected
    mock_filter.assert_called_once()
    kwargs = mock_filter.call_args.kwargs
    assert kwargs["filter_key"] == "status"
    assert kwargs["filter_value"] == "ok"


def test_tools_call_upload_data_or_file(fake_req):
    expected = {"status": "success", "blob_name": "notes.json", "manifest_status": "updated"}
    with patch("OmniFlowCentral.tools_call.upload_data_or_file", return_value=expected) as mock_upload:
        req = fake_req(
            json_body={
                "tool": "upload_data_or_file",
                "params": {"target_blob_name": "notes.json", "file_content": {"foo": "bar"}},
            }
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == expected
        mock_upload.assert_called_once()
        kwargs = mock_upload.call_args.kwargs
        assert kwargs["user_id"] == "alice"
        assert kwargs["params"]["target_blob_name"] == "notes.json"


def test_tools_call_add_new_data(fake_req):
    expected = {"status": "success", "entry_count": 1, "manifest_status": "updated"}
    with patch("OmniFlowCentral.tools_call.add_new_data", return_value=expected) as mock_add:
        req = fake_req(
            json_body={
                "tool": "add_new_data",
                "params": {"target_blob_name": "list.json", "new_entry": {"foo": "bar"}},
            }
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == expected
        mock_add.assert_called_once()
        kwargs = mock_add.call_args.kwargs
        assert kwargs["user_id"] == "alice"
        assert kwargs["params"]["new_entry"] == {"foo": "bar"}


def test_tools_call_update_data_entry(fake_req):
    expected = {
        "status": "success",
        "message": "Updated id=1 in 'list.json'.",
        "updated_key": "status",
        "updated_value": "ok",
        "manifest_status": "updated",
    }
    with patch("OmniFlowCentral.tools_call.update_data_entry", return_value=expected) as mock_update:
        req = fake_req(
            json_body={
                "tool": "update_data_entry",
                "params": {
                    "target_blob_name": "list.json",
                    "find_key": "id",
                    "find_value": "1",
                    "update_key": "status",
                    "update_value": "ok",
                },
            }
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == expected
        mock_update.assert_called_once()
        kwargs = mock_update.call_args.kwargs
        assert kwargs["user_id"] == "alice"
        assert kwargs["params"]["find_key"] == "id"
        assert kwargs["params"]["update_value"] == "ok"


def test_tools_call_remove_data_entry(fake_req):
    expected = {
        "status": "success",
        "message": "Removed id=1 from 'list.json'.",
        "manifest_status": "updated",
    }
    with patch("OmniFlowCentral.tools_call.remove_data_entry", return_value=expected) as mock_remove:
        req = fake_req(
            json_body={
                "tool": "remove_data_entry",
                "params": {
                    "target_blob_name": "list.json",
                    "find_key": "id",
                    "find_value": "1",
                },
            }
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == expected
        mock_remove.assert_called_once()
        kwargs = mock_remove.call_args.kwargs
        assert kwargs["user_id"] == "alice"
        assert kwargs["params"]["find_key"] == "id"


def test_tools_call_manage_files(fake_req):
    expected = {"status": "success", "operation": "list", "files": [], "manifest_status": "missing"}
    with patch("OmniFlowCentral.tools_call.manage_files", return_value=expected) as mock_manage:
        req = fake_req(
            json_body={
                "tool": "manage_files",
                "params": {"operation": "list", "prefix": "notes/"},
            }
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == expected
        mock_manage.assert_called_once()
        kwargs = mock_manage.call_args.kwargs
        assert kwargs["user_id"] == "alice"
        assert kwargs["params"]["operation"] == "list"


def test_tools_call_dataset_search(fake_req):
    result = {"status": "success", "hits": [], "total": 0}
    with patch("OmniFlowCentral.tools_call.dataset_search", return_value=result) as mock_search:
        req = fake_req(
            json_body={
                "tool": "dataset_search",
                "params": {"q": "notes", "tags_any": ["planning"], "limit": 5},
            }
        )
        resp = tools_call.main(req)
        assert resp.status_code == 200
        body = json.loads(resp.get_body().decode("utf-8"))
        assert body["result"] == result
        mock_search.assert_called_once()
        kwargs = mock_search.call_args.kwargs
        assert kwargs["user_id"] == "alice"
        assert kwargs["params"]["q"] == "notes"
