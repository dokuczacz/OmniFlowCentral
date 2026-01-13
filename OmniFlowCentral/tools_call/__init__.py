import json
import logging
import os

import azure.functions as func

from shared.blob_ops import (
    ToolError,
    DEFAULT_MAX_BYTES_PER_FILE,
    DEFAULT_READ_MANY_FILES,
    DEFAULT_TAIL_BYTES,
    DEFAULT_TAIL_LINES,
    delete_blob,
    get_filtered_data,
    list_blobs,
    read_blob,
    read_many_blobs,
    upload_blob,
)
from shared.data_ops import (
    add_new_data,
    dataset_search,
    eli_acts_query,
    query_dataset,
    manage_files,
    remove_data_entry,
    update_data_entry,
    upload_data_or_file,
)
from shared.error_codes import build_error_payload, get_status_code
from shared.request_contract import parse_request
from shared.tool_catalog import canonical_tool_name, apply_param_aliases
from shared.tool_specs import TOOL_SPECS
from shared.user_validator import UserValidator
from shared.response import json_response

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
        env_default = os.environ.get("OMNIFLOW_DEFAULT_USER_ID", "").strip()
        if env_default and UserValidator.validate_user_id(env_default):
            user_id = env_default
        else:
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


def _handle_read_blob(params, user_id):
    name = _require_param(params, "name")
    return read_blob(user_id=user_id, name=name)


def _handle_get_filtered_data(params, user_id):
    blob_name = params.get("target_blob_name") or params.get("blob_name") or params.get("file_name")
    if not blob_name:
        raise ToolError("MISSING_PARAM", "Missing 'target_blob_name' parameter.")
    filter_key = params.get("filter_key")
    filter_value = params.get("filter_value")
    return get_filtered_data(
        user_id=user_id,
        blob_name=blob_name,
        filter_key=filter_key,
        filter_value=filter_value,
    )


def _handle_read_many_blobs(params, user_id):
    files = params.get("files")
    if files is None:
        raise ToolError("MISSING_PARAM", "Missing 'files' parameter.")
    tail_lines = _as_int(params.get("tail_lines"), DEFAULT_TAIL_LINES)
    tail_bytes = _as_int(params.get("tail_bytes"), DEFAULT_TAIL_BYTES)
    max_bytes = _as_int(params.get("max_bytes_per_file"), DEFAULT_MAX_BYTES_PER_FILE)
    parse_json = _as_bool(params.get("parse_json"), True)
    max_files = _as_int(params.get("max_files"), DEFAULT_READ_MANY_FILES)
    return read_many_blobs(
        user_id=user_id,
        files=files,
        tail_lines=tail_lines,
        tail_bytes=tail_bytes,
        max_bytes_per_file=max_bytes,
        parse_json=parse_json,
        max_files=max_files,
    )


def _handle_upload_data_or_file(params, user_id):
    return upload_data_or_file(user_id=user_id, params=params)


def _handle_add_new_data(params, user_id):
    return add_new_data(user_id=user_id, params=params)


def _handle_update_data_entry(params, user_id):
    return update_data_entry(user_id=user_id, params=params)


def _handle_remove_data_entry(params, user_id):
    return remove_data_entry(user_id=user_id, params=params)


def _handle_manage_files(params, user_id):
    return manage_files(user_id=user_id, params=params)


def _handle_dataset_search(params, user_id):
    return dataset_search(user_id=user_id, params=params or {})


def _handle_eli_acts_query(params, user_id):
    return eli_acts_query(params=params or {})


def _handle_query_dataset(params, user_id):
    params = params or {}
    if not isinstance(params, dict):
        raise ToolError("VALIDATION_FAILED", "Expected object params for query_dataset.")

    params_copy = dict(params)
    accepted_params = sorted((TOOL_SPECS.get("query_dataset") or {}).get("params", {}).keys())

    warnings = []
    nested_filters = params_copy.get("filters")
    if nested_filters is not None:
        if not isinstance(nested_filters, dict):
            raise ToolError(
                "VALIDATION_FAILED",
                "Parameter 'filters' must be an object when provided.",
                {"accepted_params": accepted_params, "received_type": type(nested_filters).__name__},
            )
        for key, value in nested_filters.items():
            params_copy.setdefault(key, value)
        params_copy.pop("filters", None)
        warnings.append("Merged legacy nested 'filters' into top-level params (deprecated).")

    result = query_dataset(params=params_copy)

    if accepted_params:
        unknown_params = sorted([key for key in params_copy.keys() if key not in accepted_params])
        if unknown_params:
            warnings.append("Ignored unrecognized params; see 'accepted_params'.")
            result["unknown_params"] = unknown_params
            result["accepted_params"] = accepted_params

    if warnings:
        existing = result.get("warnings")
        if isinstance(existing, list):
            existing.extend(warnings)
        else:
            result["warnings"] = warnings
    return result
TOOL_HANDLERS = {
    "list_blobs": _handle_list_blobs,
    "upload_blob": _handle_upload,
    "delete_blob": _handle_delete,
    "read_blob": _handle_read_blob,
    "read_many_blobs": _handle_read_many_blobs,
    "get_filtered_data": _handle_get_filtered_data,
    "upload_data_or_file": _handle_upload_data_or_file,
    "add_new_data": _handle_add_new_data,
    "update_data_entry": _handle_update_data_entry,
    "remove_data_entry": _handle_remove_data_entry,
    "manage_files": _handle_manage_files,
    "dataset_search": _handle_dataset_search,
    "eli_acts_query": _handle_eli_acts_query,
    "query_dataset": _handle_query_dataset,
}


def _normalize_tool_and_params(contract: dict) -> tuple[str, dict]:
    """Resolve canonical tool name and apply any supported parameter aliases."""
    raw_tool = contract.get("tool") or ""
    canonical = canonical_tool_name(raw_tool)
    params = contract.get("payload", {}).get("params")
    if not isinstance(params, dict):
        params = contract.get("payload", {})
    
    # Filter out reserved fields that should not be passed to handlers
    params = {k: v for k, v in params.items() if k not in ("tool", "user_id", "trace_id")}
    params = apply_param_aliases(canonical, params)
    return canonical, params


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
    payload = contract.get("payload") or {}
    trace_id = payload.get("trace_id")
    tool, params = _normalize_tool_and_params(contract)

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

        params = params or {}
        result = handler(params, user_id)
        return _success_response(tool, user_id, trace_id, result)
    except ToolError as exc:
        logging.warning("Tool error in %s: %s", tool, exc)
        return _error_response(tool, user_id if 'user_id' in locals() else "default", trace_id, exc)
    except Exception as exc:
        logging.exception("Unexpected gpt handler failure")
        generic = ToolError("UPSTREAM_ERROR", "Internal failure.", {"detail": str(exc)}, status=500)
        return _error_response(tool, user_id if 'user_id' in locals() else "default", trace_id, generic)
