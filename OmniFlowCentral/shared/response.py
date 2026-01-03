"""
Helper for consistent JSON responses.
"""
import json

import azure.functions as func


def json_response(payload: dict, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
    )
