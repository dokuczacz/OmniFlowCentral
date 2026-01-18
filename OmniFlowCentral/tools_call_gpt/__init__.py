import logging
import os

import azure.functions as func

from shared.blob_ops import ToolError
from shared.data_ops import dataset_search, query_dataset
from shared.error_codes import build_error_payload, get_status_code
from shared.request_contract import parse_request
from shared.response import json_response


GPT_TOOL_ALLOWLIST = {
    "query_dataset",
    "dataset_search",
}


def _resolve_user_id(payload: dict) -> str:
    candidate = str(payload.get("user_id") or "").strip()
    if candidate:
        return candidate
    env_default = os.environ.get("OMNIFLOW_DEFAULT_USER_ID", "").strip()
    if env_default:
        return env_default
    return "public"


def _extract_params(contract: dict) -> dict:
    payload = contract.get("payload") or {}
    params = payload.get("params")
    if not isinstance(params, dict):
        # Allow legacy callers that send params at the top-level body.
        params = payload
    if not isinstance(params, dict):
        params = {}

    # Reserved fields must not leak into the tool params.
    return {k: v for k, v in params.items() if k not in ("tool", "user_id", "trace_id")}


def _success(tool: str, user_id: str, trace_id: str | None, result: dict) -> func.HttpResponse:
    payload = {"status": "success", "tool": tool, "user_id": user_id, "result": result}
    if trace_id:
        payload["trace_id"] = trace_id
    return json_response(payload, status=200)


def _error(tool: str, user_id: str, trace_id: str | None, code: str, message: str, details=None) -> func.HttpResponse:
    payload = build_error_payload(code, message=message, details=details)
    payload.update({"tool": tool, "user_id": user_id})
    if trace_id:
        payload["trace_id"] = trace_id
    return json_response(payload, status=get_status_code(code, 400))


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("gpt_tools_handler_gpt: received request")

    contract = parse_request(req)
    tool = (contract.get("tool") or "").strip()
    payload = contract.get("payload") or {}
    trace_id = payload.get("trace_id")

    user_id = _resolve_user_id(payload)

    if not tool:
        return _error(tool, user_id, trace_id, "MISSING_PARAM", "Missing 'tool' parameter.")

    if tool not in GPT_TOOL_ALLOWLIST:
        return _error(tool, user_id, trace_id, "INVALID_TOOL", f"Unsupported tool '{tool}' for GPT endpoint.")

    params = _extract_params(contract)

    try:
        if tool == "dataset_search":
            result = dataset_search(user_id=user_id, params=params)
        else:
            result = query_dataset(params=params)
        return _success(tool, user_id, trace_id, result)
    except ToolError as exc:
        logging.warning("Tool error in %s: %s", tool, exc)
        return _error(tool, user_id, trace_id, exc.code, exc.message, details=exc.details)
    except Exception as exc:
        logging.exception("Unexpected GPT handler failure")
        details = {"detail": str(exc)}
        return _error(tool, user_id, trace_id, "UPSTREAM_ERROR", "Internal failure.", details=details)
