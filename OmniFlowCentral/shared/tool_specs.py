"""
Metadata for App2 tools exposed via GPT handler and capabilities feed.
"""
TOOL_SPECS = {
    "list_blobs": {
        "description": "List blobs inside the requesting user's namespace.",
        "method": "POST",
        "params": {
            "prefix": "optional string",
            "max_results": "optional int (default 200, max 1000)",
            "timeout_seconds": "optional int (1-60, default 10)",
        },
    },
    "upload_blob": {
        "description": "Upload textual content into the user's namespace.",
        "method": "POST",
        "params": {
            "name": "string (relative blob path)",
            "content": "string (UTF-8 payload)",
            "overwrite": "optional bool (default true)",
        },
    },
    "delete_blob": {
        "description": "Delete a blob within the user's namespace.",
        "method": "POST",
        "params": {
            "name": "string (relative blob path)",
        },
    },
}
