import logging

import azure.functions as func

from shared.response import json_response
from shared.tool_specs import TOOL_SPECS


GPT_TOOL_ALLOWLIST = (
    "query_dataset",
    "dataset_search",
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("tools_capabilities_gpt: start")
    capabilities = []

    for name in GPT_TOOL_ALLOWLIST:
        spec = TOOL_SPECS.get(name) or {}
        capabilities.append(
            {
                "name": name,
                "description": spec.get("description", ""),
                "method": spec.get("method", "POST"),
                "params": spec.get("params", {}),
            }
        )

    return json_response({"capabilities": capabilities}, status=200)
