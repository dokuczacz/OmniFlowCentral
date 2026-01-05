import logging

import azure.functions as func

from shared.blob_ops import ToolError, read_blob
from shared.error_codes import build_error_payload, get_status_code
from shared.request_contract import parse_request
from shared.response import json_response
from shared.user_validator import UserValidator


def _resolve_user_id(req: func.HttpRequest, payload: dict) -> str:
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


def _error_response(user_id: str, exc: ToolError) -> func.HttpResponse:
    payload = build_error_payload(exc.code, message=exc.message, details=exc.details)
    payload.update({"user_id": user_id})
    status_code = exc.status or get_status_code(exc.code, 400)
    return json_response(payload, status=status_code)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("read_blob_file: start")
    contract = parse_request(req)
    payload = contract.get("payload") or {}
    file_name = req.params.get("file_name") or payload.get("file_name")
    user_id = "default"
    try:
        if not file_name:
            raise ToolError("MISSING_PARAM", "Missing 'file_name' parameter.")
        user_id = _resolve_user_id(req, payload)
        result = read_blob(user_id=user_id, name=file_name)
        return json_response({"status": "success", "result": result}, status=200)
    except ToolError as exc:
        logging.warning("read_blob_file error: %s", exc)
        return _error_response(user_id, exc)
