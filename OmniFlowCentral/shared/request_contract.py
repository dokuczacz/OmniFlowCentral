"""Shared request parsing helper that normalizes query + JSON body into a contract.

This helper is intentionally minimal and defensive: it never raises on malformed JSON
and always returns a dict with keys: `tool` (str) and `payload` (dict).
"""
from __future__ import annotations
from typing import Any, Dict


def parse_request(req) -> Dict[str, Any]:
    """Normalize an Azure Functions HttpRequest-like object into a contract.

    Behavior:
    - Prefer query params (`req.params`) for top-level fields, falling back to JSON body.
    - `tool` is mandatory for the callers — this helper returns an empty string if missing.
    - Returns {'tool': str, 'payload': dict} where payload is the merged JSON body.
    """
    params = getattr(req, "params", {}) or {}
    body = {}
    try:
        # many test fakes implement get_json(); silence exceptions
        body = req.get_json() or {}
    except Exception:
        body = {}

    # ensure both are dict-like
    if not isinstance(params, dict):
        try:
            params = dict(params)
        except Exception:
            params = {}
    if not isinstance(body, dict):
        body = {}

    # Some dispatchers (including certain Custom GPT Actions setups) may wrap
    # the entire JSON payload under a top-level "params" object:
    #   {"params": {"tool": "...", "params": {...}}}
    # Normalize that into the expected root {"tool": "...", ...} shape.
    if "tool" not in body and isinstance(body.get("params"), dict) and "tool" in body["params"]:
        body = body["params"]

    tool = (params.get("tool") or body.get("tool") or "").strip()

    # The payload is the JSON body; keep it simple for now.
    payload: Dict[str, Any] = dict(body)

    return {"tool": tool, "payload": payload}
