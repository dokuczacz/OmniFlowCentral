"""
User extraction and validation helper shared between App1 and App2.
"""
import logging
import re
from typing import Tuple

try:
    import azure.functions as func
except ImportError:  # pragma: no cover
    class DummyHttpRequest:
        def __init__(self, headers=None, params=None, body=b""):
            self.headers = headers or {}
            self.params = params or {}
            self._body = body

        def get_json(self):
            import json
            if not self._body:
                return {}
            return json.loads(self._body.decode("utf-8"))

    func = type("func", (), {"HttpRequest": DummyHttpRequest})


class UserValidator:
    USER_ID_SOURCES = [
        "user_id",
        "x_user_id",
        "userId",
        "user-id",
    ]

    @staticmethod
    def get_user_id_from_request(req: func.HttpRequest) -> Tuple[str, bool]:
        user_id = req.headers.get("X-User-Id")
        if user_id and user_id.strip():
            logging.debug("User ID extracted from header: %s", user_id)
            return user_id.strip(), True

        user_id = req.params.get("user_id") or req.params.get("userId")
        if user_id and str(user_id).strip():
            logging.debug("User ID extracted from query: %s", user_id)
            return str(user_id).strip(), True

        try:
            body = req.get_json()
            if isinstance(body, dict):
                for key in ("user_id", "userId"):
                    candidate = body.get(key)
                    if candidate and str(candidate).strip():
                        logging.debug("User ID extracted from body: %s", candidate)
                        return str(candidate).strip(), True
        except Exception:
            logging.debug("Failed to parse body for user_id", exc_info=True)

        return "default", False

    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        if not user_id or not user_id.strip():
            return False
        normalized = user_id.strip()
        if len(normalized) < 3 or len(normalized) > 64:
            return False
        return bool(re.match(r"^[a-zA-Z0-9._-]+$", normalized))


def extract_user_id(req: func.HttpRequest) -> str:
    user_id, _ = UserValidator.get_user_id_from_request(req)
    return user_id
