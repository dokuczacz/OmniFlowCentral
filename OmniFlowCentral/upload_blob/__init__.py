import logging

import azure.functions as func

from shared.blob_ops import ToolError, upload_blob
from shared.error_codes import build_error_payload, get_status_code
from shared.request_contract import parse_request
from shared.response import json_response
from shared.user_validator import extract_user_id


def _to_bool(value, default=True):
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")


def _error_response(exc: ToolError) -> func.HttpResponse:
    payload = build_error_payload(exc.code, message=exc.message, details=exc.details)
    status = exc.status or get_status_code(exc.code, 400)
    return json_response(payload, status=status)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("upload_blob: start")
    contract = parse_request(req)
    payload = contract.get("payload") or {}
    name = req.params.get("name") or payload.get("name")
    content = payload.get("content") or req.params.get("content")
    overwrite = _to_bool(payload.get("overwrite") or req.params.get("overwrite"))
    try:
        result = upload_blob(
            name=name,
            content=content,
            overwrite=overwrite,
            user_id=extract_user_id(req),
        )
        return json_response({"status": "success", "result": result}, status=200)
    except ToolError as exc:
        logging.warning("upload_blob tool error: %s", exc)
        return _error_response(exc)
