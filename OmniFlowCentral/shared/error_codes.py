"""
Structured error codes for the GPT tooling layer.
"""
from typing import Any, Dict, Optional

ERROR_REGISTRY = {
    "INVALID_TOOL": {"status": 400, "message": "Requested tool is not supported."},
    "MISSING_PARAM": {"status": 400, "message": "Required parameter is missing."},
    "VALIDATION_FAILED": {"status": 400, "message": "Input validation failed."},
    "UPSTREAM_ERROR": {"status": 502, "message": "Upstream storage error."},
    "AUTH_FAILED": {"status": 401, "message": "Authentication failed."},
}


def build_error_payload(code: str, message: Optional[str] = None, details: Optional[Any] = None) -> Dict[str, Any]:
    info = ERROR_REGISTRY.get(code, {"status": 400, "message": "Unknown error."})
    payload = {
        "status": "error",
        "code": code,
        "message": message or info["message"],
    }
    if details is not None:
        payload["details"] = details
    return payload


def get_status_code(code: str, default: int = 400) -> int:
    return ERROR_REGISTRY.get(code, {}).get("status", default)
