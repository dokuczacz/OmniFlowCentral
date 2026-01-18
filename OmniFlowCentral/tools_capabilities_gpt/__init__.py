import logging

import azure.functions as func

from shared.response import json_response


GPT_CAPABILITIES = [
    {
        "name": "query_dataset",
        "description": "Search the public ELI acts index with optional bounded text excerpts (eli_acts only).",
        "method": "POST",
        "params": {
            "dataset": "string (eli_acts)",
            "q": "optional string",
            "limit": "optional int (default 10, max 100)",
            "fetch_content": "optional bool (default false)",
            "year": "optional int",
            "publisher": "optional string",
            "status": "optional string",
            "pageId": "optional string (ELI id like DU/2025/1882)",
            "recordIndex": "optional int (act position/pos)",
            "content_slice": "optional object {start:int, length:int} (defaults 0/2048, max length 4096)",
        },
    },
    {
        "name": "dataset_search",
        "description": "Discover manifest entries (datasets/tags) in the public namespace.",
        "method": "POST",
        "params": {
            "q": "optional string",
            "tags_any": "optional array[string]",
            "tags_all": "optional array[string]",
            "category": "optional string (recommended: dataset)",
            "since": "optional ISO8601 datetime",
            "until": "optional ISO8601 datetime",
            "limit": "optional int (default 20, max 100)",
            "cursor": "optional string (updated_at|blob_name)",
            "user_id": "optional string (recommended: public)",
        },
    },
]


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("tools_capabilities_gpt: start")
    return json_response({"capabilities": GPT_CAPABILITIES}, status=200)
