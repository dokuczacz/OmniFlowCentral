import json
import logging

import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("tools_capabilities: start")
    caps = {
        "capabilities": [
            {
                "name": "list_blobs",
                "description": "List blobs in the configured storage container",
                "method": "POST",
                "params": {
                    "prefix": "optional string",
                    "max_results": "optional int (max 1000)"
                }
            },
            {
                "name": "get_blob",
                "description": "Get blob content by name (decoded as UTF-8)",
                "method": "POST",
                "params": {
                    "name": "string (blob name)"
                }
            }
        ]
    }

    return func.HttpResponse(
        json.dumps(caps, ensure_ascii=False),
        status_code=200,
        mimetype="application/json",
    )
