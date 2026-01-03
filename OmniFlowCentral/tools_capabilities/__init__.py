import logging

import azure.functions as func

from OmniFlowCentral.shared.response import json_response
from OmniFlowCentral.shared.tool_specs import TOOL_SPECS


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("tools_capabilities: start")
    capabilities = []
    for name, spec in TOOL_SPECS.items():
        capabilities.append(
            {
                "name": name,
                "description": spec.get("description", ""),
                "method": spec.get("method", "POST"),
                "params": spec.get("params", {}),
            }
        )
    return json_response({"capabilities": capabilities}, status=200)
