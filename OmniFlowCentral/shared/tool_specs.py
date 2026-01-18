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
    "read_blob": {
        "description": "Read a blob inside the user's namespace, returning JSON or text (parameter `name` with aliases `file_name`).",
        "method": "POST",
        "params": {
            "name": "string (relative blob path)",
        },
    },
    "read_many_blobs": {
        "description": "Read multiple blobs at once with optional tail/prefix limits.",
        "method": "POST",
        "params": {
            "files": "array[string] (relative blob paths, max 25)",
            "tail_lines": "optional int (default 0)",
            "tail_bytes": "optional int (default 65536)",
            "max_bytes_per_file": "optional int (default 262144)",
            "parse_json": "optional bool (default true)",
            "max_files": "optional int (default 25)",
        },
    },
    "get_filtered_data": {
        "description": "Retrieve JSON content from a blob with optional filtering.",
        "method": "POST",
        "params": {
            "target_blob_name": "string (relative blob path)",
            "filter_key": "optional string",
            "filter_value": "optional string",
        },
    },
    "upload_data_or_file": {
        "description": "Upload JSON/text data and keep the manifest metadata in sync.",
        "method": "POST",
        "params": {
            "target_blob_name": "string (relative blob path)",
            "file_content": "string|object (content to write)",
            "display_name": "optional string",
            "summary": "optional string",
            "tags": "optional array[string]",
            "manifest_tags": "optional array[string]",
            "category": "optional string",
            "source": "optional string",
            "metadata": "optional object",
            "version": "optional string",
        },
    },
    "add_new_data": {
        "description": "Append entries to a JSON array in a blob while updating the manifest.",
        "method": "POST",
        "params": {
            "target_blob_name": "string (relative blob path)",
            "new_entry": "object|string (entry to append)",
        },
    },
    "update_data_entry": {
        "description": "Update a single record within a JSON array blob.",
        "method": "POST",
        "params": {
            "target_blob_name": "string (relative blob path)",
            "find_key": "string",
            "find_value": "string|number",
            "update_key": "string",
            "update_value": "string|number|object",
        },
    },
    "remove_data_entry": {
        "description": "Remove a single record from a JSON array blob.",
        "method": "POST",
        "params": {
            "target_blob_name": "string (relative blob path)",
            "find_key": "string",
            "find_value": "string|number",
        },
    },
    "manage_files": {
        "description": "List, delete, or rename blob files within the user namespace.",
        "method": "POST",
        "params": {
            "operation": "string (one of list/delete/rename)",
            "prefix": "optional string (list only)",
            "source_name": "string (delete/rename)",
            "target_name": "string (rename only)",
        },
    },
    "dataset_search": {
        "description": "Query the per-user manifest using filters (tags, category, date, cursor).",
        "method": "POST",
        "params": {
            "q": "optional string",
            "tags_any": "optional array[string]",
            "tags_all": "optional array[string]",
            "category": "optional string",
            "since": "optional ISO8601 datetime",
            "until": "optional ISO8601 datetime",
            "limit": "optional int (default 20, max 100)",
            "cursor": "optional string (updated_at|blob_name)",
        },
    },
    "eli_acts_query": {
        "description": "Query the Sejm ELI acts dataset (public dataset of Polish legislative acts). DEPRECATED: use query_dataset instead.",
        "method": "POST",
        "params": {
            "q": "optional string (search in title)",
            "year": "optional int (filter by year)",
            "publisher": "optional string (filter by publisher)",
            "status": "optional string (filter by status)",
            "limit": "optional int (default 10, max 50)",
        },
    },
    "query_dataset": {
        "description": "Unified dataset query tool. Search NDJSON indexes with optional full content fetching. Supports eli_acts, saos_judgments, and future datasets.",
        "method": "POST",
        "params": {
            "dataset": "string (dataset name: eli_acts, saos_judgments, etc.)",
            "q": "optional string (text search query)",
            "limit": "optional int (default 10, max 100)",
            "fetch_content": "optional bool (default false - if true, fetch full blob content for matches)",
            "year": "optional int (ELI: filter by year)",
            "publisher": "optional string (ELI: filter by publisher)",
            "status": "optional string (ELI: filter by status)",
            "court": "optional string (SAOS: filter by court name)",
            "court_type": "optional string (SAOS: filter by court type)",
            "pageId": "optional string (ELI: ELI id like DU/2025/1882; SAOS: page blob id like page_00001)",
            "recordIndex": "optional int (ELI: pos; SAOS: index within page array; requires pageId for SAOS)",
            "content_slice": "optional object {start:int, length:int} to request a bounded excerpt (defaults 0/2048 bytes, respects 2 MB cap)",
        },
    },
}
