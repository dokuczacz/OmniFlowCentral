"""
Import aliasing layer for Azure Functions.

In production, the Function App package root contains a top-level `shared` package
(`/home/site/wwwroot/shared`). Handlers may import `OmniFlowCentral.shared.<module>`.
This module aliases `OmniFlowCentral.shared.<module>` to `shared.<module>`.
"""

from __future__ import annotations

import importlib
import sys


_ALIAS_MODULES = (
    "blob_ops",
    "config",
    "data_ops",
    "error_codes",
    "gmail_client",
    "gmail_oauth",
    "logging_setup",
    "manifest_helper",
    "oauth_email",
    "request_contract",
    "response",
    "tool_specs",
    "user_validator",
)

for _name in _ALIAS_MODULES:
    try:
        _mod = importlib.import_module(f"shared.{_name}")
    except Exception:
        continue
    sys.modules[f"{__name__}.{_name}"] = _mod
    globals()[_name] = _mod
