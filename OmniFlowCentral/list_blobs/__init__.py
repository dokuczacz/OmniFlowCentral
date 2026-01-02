import logging

import azure.functions as func

from OmniFlowCentral.shared.blob_ops import ToolError, list_blobs
from OmniFlowCentral.shared.error_codes import build_error_payload, get_status_code
from OmniFlowCentral.shared.request_contract import parse_request
from OmniFlowCentral.shared.response import json_response
from OmniFlowCentral.shared.user_validator import extract_user_id

DEFAULT_MAX_RESULTS = 200
DEFAULT_TIMEOUT_SECONDS = 10


def _parse_int(value, default):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ToolError("VALIDATION_FAILED", f"Expected integer, got {value!r}.") from exc


def _error_response(exc: ToolError) -> func.HttpResponse:
    payload = build_error_payload(exc.code, message=exc.message, details=exc.details)
    status = exc.status or get_status_code(exc.code, 400)
    return json_response(payload, status=status)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("list_blobs: start")
    contract = parse_request(req)
    payload = contract.get("payload") or {}
    prefix = req.params.get("prefix") or payload.get("prefix") or ""
    try:
        result = list_blobs(
            user_id=extract_user_id(req),
            prefix=prefix,
            max_results=_parse_int(req.params.get("max_results") or payload.get("max_results"), DEFAULT_MAX_RESULTS),
            timeout_seconds=_parse_int(
                req.params.get("timeout_seconds") or payload.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS
            ),
        )
        return json_response({"status": "success", "result": {"items": result}}, status=200)
    except ToolError as exc:
        logging.warning("list_blobs tool error: %s", exc)
        return _error_response(exc)
