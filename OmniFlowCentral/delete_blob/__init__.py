import logging

import azure.functions as func

from OmniFlowCentral.shared.blob_ops import ToolError, delete_blob
from OmniFlowCentral.shared.error_codes import build_error_payload, get_status_code
from OmniFlowCentral.shared.request_contract import parse_request
from OmniFlowCentral.shared.response import json_response
from OmniFlowCentral.shared.user_validator import extract_user_id


def _error_response(exc: ToolError) -> func.HttpResponse:
    payload = build_error_payload(exc.code, message=exc.message, details=exc.details)
    status = exc.status or get_status_code(exc.code, 400)
    return json_response(payload, status=status)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("delete_blob: start")
    contract = parse_request(req)
    payload = contract.get("payload") or {}
    name = req.params.get("name") or payload.get("name")
    try:
        result = delete_blob(
            name=name,
            user_id=extract_user_id(req),
        )
        return json_response({"status": "success", "result": result}, status=200)
    except ToolError as exc:
        logging.warning("delete_blob tool error: %s", exc)
        return _error_response(exc)
