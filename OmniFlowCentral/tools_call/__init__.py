import json
import logging

import azure.functions as func

from OmniFlowCentral.shared.blob_ops import ToolError, delete_blob, list_blobs, upload_blob
from OmniFlowCentral.shared.error_codes import build_error_payload, get_status_code
from OmniFlowCentral.shared.request_contract import parse_request
from OmniFlowCentral.shared.tool_specs import TOOL_SPECS
from OmniFlowCentral.shared.user_validator import UserValidator
from OmniFlowCentral.shared.response import json_response

DEFAULT_MAX_RESULTS = 200
DEFAULT_TIMEOUT_SECONDS = 10


def _as_int(value, default_value):
    if value is None:
        return default_value
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ToolError("VALIDATION_FAILED", f"Expected integer, got {value!r}.", {"field": value}) from exc


def _as_bool(value, default_value):
    if value in (None, ""):
        return default_value
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


def _require_param(params, name):
    value = params.get(name)
    if value is None:
        raise ToolError("MISSING_PARAM", f"Missing required parameter '{name}'.")
    return value


def _resolve_user_id(req, payload):
    user_id, detected = UserValidator.get_user_id_from_request(req)
    if not detected and (payload_user := payload.get("user_id")):
        candidate = str(payload_user).strip()
        if candidate:
            if not UserValidator.validate_user_id(candidate):
                raise ToolError("VALIDATION_FAILED", "Invalid user_id format.")
            user_id = candidate
            detected = True
    if not detected:
        user_id = "default"
    return user_id


def _handle_list_blobs(params, user_id):
    prefix = params.get("prefix")
    result = list_blobs(
        user_id=user_id,
        prefix=prefix or "",
        max_results=_as_int(params.get("max_results"), DEFAULT_MAX_RESULTS),
        timeout_seconds=_as_int(params.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS),
    )
    return {"items": result}


def _handle_upload(params, user_id):
    name = _require_param(params, "name")
    content = _require_param(params, "content")
    overwrite = _as_bool(params.get("overwrite"), True)
    return upload_blob(name=name, content=content, user_id=user_id, overwrite=overwrite)


def _handle_delete(params, user_id):
    name = _require_param(params, "name")
    return delete_blob(name=name, user_id=user_id)


TOOL_HANDLERS = {
    "list_blobs": _handle_list_blobs,
    "upload_blob": _handle_upload,
    "delete_blob": _handle_delete,
}


def _error_response(tool, user_id, trace_id, exc: ToolError) -> func.HttpResponse:
    payload = build_error_payload(exc.code, message=exc.message, details=exc.details)
    payload.update({"tool": tool, "user_id": user_id})
    if trace_id:
        payload["trace_id"] = trace_id
    status_code = exc.status or get_status_code(exc.code, 400)
    return json_response(payload, status=status_code)


def _success_response(tool, user_id, trace_id, result: dict) -> func.HttpResponse:
    payload = {"status": "success", "tool": tool, "user_id": user_id, "result": result}
    if trace_id:
        payload["trace_id"] = trace_id
    return json_response(payload, status=200)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("gpt_tools_handler: received request")
    contract = parse_request(req)
    tool = contract.get("tool") or ""
    payload = contract.get("payload") or {}
    trace_id = payload.get("trace_id")

    if not tool:
        error = ToolError("MISSING_PARAM", "Missing 'tool' parameter.")
        return _error_response(tool, "default", trace_id, error)

    if tool not in TOOL_SPECS:
        error = ToolError("INVALID_TOOL", f"Unsupported tool '{tool}'.")
        return _error_response(tool, "default", trace_id, error)

    handler = TOOL_HANDLERS.get(tool)
    if handler is None:
        error = ToolError("INVALID_TOOL", f"Unsupported tool '{tool}'.")
        return _error_response(tool, "default", trace_id, error)

    try:
        user_id = _resolve_user_id(req, payload)
        if not UserValidator.validate_user_id(user_id):
            raise ToolError("VALIDATION_FAILED", "User identifier failed validation.")

        params = payload.get("params")
        if not isinstance(params, dict):
            params = payload
        result = handler(params, user_id)
        return _success_response(tool, user_id, trace_id, result)
    except ToolError as exc:
        logging.warning("Tool error in %s: %s", tool, exc)
        return _error_response(tool, user_id if 'user_id' in locals() else "default", trace_id, exc)
    except Exception as exc:
        logging.exception("Unexpected gpt handler failure")
        generic = ToolError("UPSTREAM_ERROR", "Internal failure.", {"detail": str(exc)}, status=500)
        return _error_response(tool, user_id if 'user_id' in locals() else "default", trace_id, generic)
