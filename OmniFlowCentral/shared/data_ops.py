import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from shared.blob_ops import ToolError, RESPONSE_SOFT_CAP
from shared.config import AzureConfig
from shared.manifest_helper import (
    build_manifest_entry,
    load_manifest,
    remove_manifest_entry,
    rename_manifest_entry,
    upsert_manifest_entry,
)

DEFAULT_NAMESPACE_PREFIX = 'users'


def _user_prefix(user_id: str) -> str:
    normalized = user_id.strip().replace('/', '_').replace('\\', '_') or 'default'
    return f'{DEFAULT_NAMESPACE_PREFIX}/{normalized}'


def _apply_user_prefix(name: str, user_id: str) -> str:
    sanitized = name.strip().lstrip('/')
    prefix = _user_prefix(user_id)
    if sanitized.startswith(prefix + '/'):
        return sanitized
    return f'{prefix}/{sanitized}'


def _connect_container():
    if not AzureConfig.CONNECTION_STRING:
        raise ToolError('UPSTREAM_ERROR', 'Missing Azure storage connection string.')
    if not AzureConfig.CONTAINER_NAME:
        raise ToolError('UPSTREAM_ERROR', 'Missing Azure container name.')
    try:
        service_client = BlobServiceClient.from_connection_string(AzureConfig.CONNECTION_STRING)
        return service_client.get_container_client(AzureConfig.CONTAINER_NAME)
    except AzureError as exc:
        logging.exception('data_ops.upload_data: storage init failure')
        raise ToolError(
            'UPSTREAM_ERROR',
            'Unable to initialize storage.',
            {'detail': str(exc)},
            status=502,
        )


def _prepare_payload(params: Dict[str, Any]) -> Tuple[str, Any]:
    target_blob_name = params.get('target_blob_name') or params.get('file_name')
    file_content = params.get('file_content') if 'file_content' in params else params.get('content')
    if not target_blob_name or file_content is None:
        raise ToolError(
            'MISSING_PARAM',
            "Both 'target_blob_name' and 'file_content' are required.",
        )
    return str(target_blob_name).strip(), file_content


def _serialize_content(value: Any) -> Tuple[bytes, str]:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, indent=2, ensure_ascii=False)
        content_type = 'application/json'
    else:
        text = str(value)
        content_type = 'text/plain'
    payload_bytes = text.encode('utf-8')
    return payload_bytes, content_type


def upload_data_or_file(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    target_blob_name, file_content = _prepare_payload(params)
    payload_bytes, content_type = _serialize_content(file_content)
    container_client = _connect_container()
    namespaced = _apply_user_prefix(target_blob_name, user_id)
    blob_client = container_client.get_blob_client(namespaced)
    try:
        blob_client.upload_blob(
            payload_bytes,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
    except AzureError as exc:
        logging.exception('upload_data_or_file: write failed')
        raise ToolError('UPSTREAM_ERROR', 'Unable to upload content.', {'detail': str(exc)}, status=502)

    manifest_status = 'updated'
    manifest_error: Optional[str] = None
    try:
        entry = build_manifest_entry(
            namespaced=namespaced,
            target_blob_name=target_blob_name,
            payload=params,
            content_type=content_type,
            size=len(payload_bytes),
        )
        upsert_manifest_entry(container_client, user_id, entry)
    except ToolError as exc:
        logging.warning('upload_data_or_file: manifest update failed: %s', exc)
        manifest_status = 'failed'
        manifest_error = exc.message
    except Exception as exc:
        logging.exception('upload_data_or_file: manifest update unexpected failure')
        manifest_status = 'failed'
        manifest_error = str(exc)

    response = {
        'status': 'success',
        'message': 'File uploaded successfully.',
        'user_id': user_id,
        'blob_name': target_blob_name,
        'storage_location': namespaced,
        'content_type': content_type,
        'size_bytes': len(payload_bytes),
        'manifest_status': manifest_status,
    }
    if manifest_error:
        response['manifest_error'] = manifest_error
    return response


def _prepare_array_blob(params: Dict[str, Any]) -> Tuple[str, Any]:
    target_blob_name = params.get('target_blob_name') or params.get('file_name')
    if not target_blob_name or not isinstance(target_blob_name, str):
        raise ToolError('MISSING_PARAM', "Missing or invalid 'target_blob_name'.")
    target_blob_name = target_blob_name.strip()
    if not target_blob_name:
        raise ToolError('MISSING_PARAM', "Missing or invalid 'target_blob_name'.")
    new_entry = params.get('new_entry')
    if new_entry is None:
        raise ToolError('MISSING_PARAM', "Missing 'new_entry'.")
    return target_blob_name, new_entry


def _deserialize_entry(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _load_existing_list(blob_client) -> List[Any]:
    try:
        raw = blob_client.download_blob().readall().decode('utf-8')
    except ResourceNotFoundError:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolError(
            'UPSTREAM_ERROR',
            'Existing blob contains invalid JSON.',
            {'detail': str(exc)},
            status=500,
        )
    if isinstance(parsed, list):
        return parsed.copy()
    return [parsed]


def add_new_data(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    target_blob_name, raw_entry = _prepare_array_blob(params)
    entry = _deserialize_entry(raw_entry)
    container_client = _connect_container()
    namespaced = _apply_user_prefix(target_blob_name, user_id)
    blob_client = container_client.get_blob_client(namespaced)

    existing = _load_existing_list(blob_client)
    existing.append(entry)

    payload_bytes = json.dumps(existing, indent=2, ensure_ascii=False).encode('utf-8')
    try:
        blob_client.upload_blob(
            payload_bytes,
            overwrite=True,
            content_settings=ContentSettings(content_type='application/json'),
        )
    except AzureError as exc:
        logging.exception('add_new_data: write failed')
        raise ToolError('UPSTREAM_ERROR', 'Unable to append data.', {'detail': str(exc)}, status=502)

    manifest_status = 'updated'
    manifest_error: Optional[str] = None
    try:
        manifest_entry = build_manifest_entry(
            namespaced=namespaced,
            target_blob_name=target_blob_name,
            payload=params,
            content_type='application/json',
            size=len(payload_bytes),
        )
        upsert_manifest_entry(container_client, user_id, manifest_entry)
    except ToolError as exc:
        logging.warning('add_new_data: manifest update failed: %s', exc)
        manifest_status = 'failed'
        manifest_error = exc.message
    except Exception as exc:
        logging.exception('add_new_data: manifest update unexpected failure')
        manifest_status = 'failed'
        manifest_error = str(exc)

    response = {
        'status': 'success',
        'message': f"Entry appended to '{target_blob_name}'.",
        'entry_count': len(existing),
        'user_id': user_id,
        'manifest_status': manifest_status,
    }
    if manifest_error:
        response['manifest_error'] = manifest_error
    return response


def _prepare_update_payload(params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    target_blob_name = params.get('target_blob_name') or params.get('file_name')
    if not target_blob_name or not isinstance(target_blob_name, str):
        raise ToolError('MISSING_PARAM', "Missing or invalid 'target_blob_name'.")
    target_blob_name = target_blob_name.strip()
    if not target_blob_name:
        raise ToolError('MISSING_PARAM', "Missing or invalid 'target_blob_name'.")

    find_key = params.get('find_key')
    find_value = params.get('find_value')
    update_key = params.get('update_key')
    update_value = params.get('update_value')
    if not find_key or not update_key or find_value is None:
        raise ToolError('MISSING_PARAM', "Missing find/update parameters.")

    return target_blob_name, {
        'find_key': str(find_key).strip(),
        'find_value': find_value,
        'update_key': str(update_key).strip(),
        'update_value': update_value,
    }


def _find_entry(entries: List[Any], find_key: str, find_value: Any) -> Optional[Dict[str, Any]]:
    match = None
    find_value_str = str(find_value).lower()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get(find_key, '')).lower() == find_value_str:
            match = entry
            break
    return match


def update_data_entry(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    target_blob_name, payload = _prepare_update_payload(params)
    container_client = _connect_container()
    namespaced = _apply_user_prefix(target_blob_name, user_id)
    blob_client = container_client.get_blob_client(namespaced)

    entries = _load_existing_list(blob_client)
    target_entry = _find_entry(entries, payload['find_key'], payload['find_value'])
    if not target_entry:
        raise ToolError(
            'NOT_FOUND',
            f"Record not found: {payload['find_key']}={payload['find_value']}",
            status=404,
        )

    target_entry[payload['update_key']] = payload['update_value']
    payload_bytes = json.dumps(entries, indent=2, ensure_ascii=False).encode('utf-8')
    try:
        blob_client.upload_blob(
            payload_bytes,
            overwrite=True,
            content_settings=ContentSettings(content_type='application/json'),
        )
    except AzureError as exc:
        logging.exception('update_data_entry: write failed')
        raise ToolError('UPSTREAM_ERROR', 'Unable to update data.', {'detail': str(exc)}, status=502)

    manifest_status = 'updated'
    manifest_error: Optional[str] = None
    try:
        manifest_entry = build_manifest_entry(
            namespaced=namespaced,
            target_blob_name=target_blob_name,
            payload=params,
            content_type='application/json',
            size=len(payload_bytes),
        )
        upsert_manifest_entry(container_client, user_id, manifest_entry)
    except ToolError as exc:
        logging.warning('update_data_entry: manifest update failed: %s', exc)
        manifest_status = 'failed'
        manifest_error = exc.message
    except Exception as exc:
        logging.exception('update_data_entry: manifest update unexpected failure')
        manifest_status = 'failed'
        manifest_error = str(exc)

    response = {
        'status': 'success',
        'message': f"Updated {payload['find_key']}={payload['find_value']} in '{target_blob_name}'.",
        'updated_key': payload['update_key'],
        'updated_value': payload['update_value'],
        'user_id': user_id,
        'manifest_status': manifest_status,
    }
    if manifest_error:
        response['manifest_error'] = manifest_error
    return response


def remove_data_entry(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    target_blob_name, payload = _prepare_update_payload(params)
    container_client = _connect_container()
    namespaced = _apply_user_prefix(target_blob_name, user_id)
    blob_client = container_client.get_blob_client(namespaced)

    entries = _load_existing_list(blob_client)
    target_entry = _find_entry(entries, payload['find_key'], payload['find_value'])
    if not target_entry:
        raise ToolError(
            'NOT_FOUND',
            f"Record not found: {payload['find_key']}={payload['find_value']}",
            status=404,
        )

    entries = [entry for entry in entries if entry is not target_entry]
    payload_bytes = json.dumps(entries, indent=2, ensure_ascii=False).encode('utf-8')
    try:
        blob_client.upload_blob(
            payload_bytes,
            overwrite=True,
            content_settings=ContentSettings(content_type='application/json'),
        )
    except AzureError as exc:
        logging.exception('remove_data_entry: write failed')
        raise ToolError('UPSTREAM_ERROR', 'Unable to remove data.', {'detail': str(exc)}, status=502)

    manifest_status = 'updated'
    manifest_error: Optional[str] = None
    try:
        manifest_entry = build_manifest_entry(
            namespaced=namespaced,
            target_blob_name=target_blob_name,
            payload=params,
            content_type='application/json',
            size=len(payload_bytes),
        )
        upsert_manifest_entry(container_client, user_id, manifest_entry)
    except ToolError as exc:
        logging.warning('remove_data_entry: manifest update failed: %s', exc)
        manifest_status = 'failed'
        manifest_error = exc.message
    except Exception as exc:
        logging.exception('remove_data_entry: manifest update unexpected failure')
        manifest_status = 'failed'
        manifest_error = str(exc)

    response = {
        'status': 'success',
        'message': f"Removed {payload['find_key']}={payload['find_value']} from '{target_blob_name}'.",
        'user_id': user_id,
        'manifest_status': manifest_status,
    }
    if manifest_error:
        response['manifest_error'] = manifest_error
    return response


def _sanitize_prefix(prefix: Optional[str]) -> str:
    return str(prefix or "").strip().lstrip("/")


def _list_user_blobs(container, user_id: str, user_prefix: str, prefix: Optional[str]) -> Dict[str, Any]:
    sanitized = _sanitize_prefix(prefix)
    base_prefix = f"{user_prefix}/"
    full_prefix = f"{base_prefix}{sanitized}" if sanitized else base_prefix
    blobs = container.list_blobs(name_starts_with=full_prefix)
    files = [blob.name[len(base_prefix) :] for blob in blobs if isinstance(blob.name, str) and blob.name.startswith(base_prefix)]
    return {
        "status": "success",
        "user_id": user_id,
        "operation": "list",
        "prefix": prefix or "",
        "files": files,
        "count": len(files),
        "message": f"Successfully listed {len(files)} files.",
    }


def _delete_blob(container, user_prefix: str, user_id: str, source_name: str) -> Dict[str, Any]:
    if not source_name or not source_name.strip():
        raise ToolError("MISSING_PARAM", "Missing 'source_name' for delete operation.")
    namespaced = f"{user_prefix}/{source_name.strip()}"
    blob_client = container.get_blob_client(namespaced)
    blob_client.delete_blob()
    removed = remove_manifest_entry(container, user_id, namespaced)
    manifest_status = "updated" if removed else "missing"
    result = {
        "status": "success",
        "user_id": user_id,
        "operation": "delete",
        "source_name": source_name,
        "message": f"Successfully deleted file: {source_name}.",
        "manifest_status": manifest_status,
    }
    return result


def _rename_blob(container, user_prefix: str, user_id: str, source_name: str, target_name: str) -> Dict[str, Any]:
    if not source_name or not target_name:
        raise ToolError("MISSING_PARAM", "Missing 'source_name' or 'target_name' for rename.")
    source_ns = f"{user_prefix}/{source_name.strip()}"
    target_ns = f"{user_prefix}/{target_name.strip()}"
    source_client = container.get_blob_client(source_ns)
    target_client = container.get_blob_client(target_ns)
    target_client.start_copy_from_url(source_client.url)
    source_client.delete_blob()
    updated = rename_manifest_entry(container, user_id, source_ns, target_ns, target_name)
    manifest_status = "updated" if updated else "missing"
    result = {
        "status": "success",
        "user_id": user_id,
        "operation": "rename",
        "source_name": source_name,
        "target_name": target_name,
        "message": f"Successfully renamed '{source_name}' to '{target_name}'.",
        "manifest_status": manifest_status,
    }
    return result


def manage_files(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    operation = (params.get("operation") or "").strip().lower()
    if not operation:
        raise ToolError("MISSING_PARAM", "Missing 'operation' parameter.")

    container_client = _connect_container()
    user_prefix = _user_prefix(user_id)

    if operation == "list":
        prefix = params.get("prefix")
        return _list_user_blobs(container_client, user_id, user_prefix, prefix)
    if operation == "delete":
        source_name = str(params.get("source_name") or "").strip()
        return _delete_blob(container_client, user_prefix, user_id, source_name)
    if operation == "rename":
        source_name = params.get("source_name")
        target_name = params.get("target_name")
        if not source_name or not target_name:
            raise ToolError("MISSING_PARAM", "Missing 'source_name' or 'target_name' for rename.")
        return _rename_blob(container_client, user_prefix, user_id, str(source_name), str(target_name))

    raise ToolError("VALIDATION_FAILED", f"Unsupported operation: {operation}.")


def _normalize_tags(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    candidate = str(value).strip()
    return [candidate.lower()] if candidate else []


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _entry_key(entry: Dict[str, Any]) -> Tuple[str, str]:
    updated = entry.get("updated_at") or entry.get("created_at") or ""
    blob = entry.get("blob_name") or ""
    return updated, blob


def dataset_search(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    q = str(params.get("q") or "").strip().lower()
    tags_any = _normalize_tags(params.get("tags_any"))
    tags_all = _normalize_tags(params.get("tags_all"))
    category = str(params.get("category") or "").strip().lower()
    since_dt = _parse_iso(str(params.get("since") or ""))
    until_dt = _parse_iso(str(params.get("until") or ""))
    limit = params.get("limit")
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 100))
    cursor = str(params.get("cursor") or "").strip()
    cursor_key: Optional[Tuple[str, str]] = None
    if cursor and "|" in cursor:
        parts = cursor.split("|", 1)
        cursor_key = (parts[0], parts[1])

    container_client = _connect_container()
    manifest = load_manifest(container_client, user_id)
    entries = manifest.get("entries", [])
    for entry in entries:
        entry.setdefault("tags", [])
        entry.setdefault("category", "")

    entries.sort(key=lambda e: e.get("blob_name", ""))
    entries.sort(key=lambda e: (e.get("updated_at") or "" or ""), reverse=True)

    filtered: List[Dict[str, Any]] = []
    for entry in entries:
        entry_tags = {str(tag).lower() for tag in entry.get("tags", []) if str(tag).strip()}
        if tags_all and not set(tags_all).issubset(entry_tags):
            continue
        if tags_any and not entry_tags.intersection(tags_any):
            continue
        if category and str(entry.get("category", "")).lower() != category:
            continue
        entry_updated = _parse_iso(entry.get("updated_at") or entry.get("created_at"))
        if since_dt and entry_updated and entry_updated < since_dt:
            continue
        if until_dt and entry_updated and entry_updated > until_dt:
            continue
        if q:
            summary = str(entry.get("summary", "")).lower()
            name = str(entry.get("display_name", "")).lower()
            if q not in summary and q not in name:
                continue
        filtered.append(entry)

    total = len(filtered)
    results: List[Dict[str, Any]] = []
    next_cursor: Optional[Tuple[str, str]] = None
    skip_to_cursor = bool(cursor_key)
    for entry in filtered:
        key = _entry_key(entry)
        if skip_to_cursor and cursor_key and key >= cursor_key:
            continue
        skip_to_cursor = False

        score = 0
        entry_tags = {str(tag).lower() for tag in entry.get("tags", []) if str(tag).strip()}
        if tags_all:
            score += len(tags_all)
        if tags_any:
            score += len(entry_tags.intersection(tags_any))
        if q and (q in str(entry.get("display_name", "")).lower() or q in str(entry.get("summary", "")).lower()):
            score += 1
        if category and str(entry.get("category", "")).lower() == category:
            score += 1

        hit = {
            "blob_name": entry.get("blob_name"),
            "display_name": entry.get("display_name"),
            "summary": entry.get("summary"),
            "tags": entry.get("tags"),
            "category": entry.get("category"),
            "source": entry.get("source"),
            "updated_at": entry.get("updated_at"),
            "created_at": entry.get("created_at"),
            "size": entry.get("size"),
            "metadata": entry.get("metadata"),
            "score": score,
        }
        results.append(hit)
        if len(results) >= limit:
            next_cursor = key
            break

    response = {
        "status": "success",
        "user_id": user_id,
        "total": total,
        "cursor": f"{next_cursor[0]}|{next_cursor[1]}" if next_cursor else None,
        "hits": results,
    }
    return response


# Dataset index registry: maps dataset names to index blob paths
DATASET_INDEX_REGISTRY = {
    "eli_acts": "users/public/datasets/eli_acts/index/acts_inforce_1.jsonl",
    "saos_judgments": "datasets/saos/judgments/index/judgments_index.jsonl",
}

QUERY_DATASET_CONTENT_SOFT_CAP = 200 * 1024


def _estimate_json_bytes(value: Any) -> int:
    try:
        return len(
            json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
    except Exception:
        return 0


def _apply_response_soft_cap(response: Dict[str, Any]) -> Dict[str, Any]:
    if not RESPONSE_SOFT_CAP:
        return response
    if _estimate_json_bytes(response) <= RESPONSE_SOFT_CAP:
        return response

    response["truncated"] = True
    response["warning"] = "Response truncated to soft cap."
    hits = response.get("hits", [])

    # First, drop full content payloads to stay under the cap.
    for hit in reversed(hits):
        if "_fullContent" in hit:
            hit.pop("_fullContent", None)
            hit["_contentTruncated"] = True
        if _estimate_json_bytes(response) <= RESPONSE_SOFT_CAP:
            response["total_returned"] = len(hits)
            return response

    # If still too large, drop hits from the end.
    while hits and _estimate_json_bytes(response) > RESPONSE_SOFT_CAP:
        hits.pop()
    response["hits"] = hits
    response["total_returned"] = len(hits)
    return response


def query_dataset(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified dataset query tool. Searches NDJSON indexes with optional content fetching.
    
    Supports:
    - dataset: name of the dataset (eli_acts, saos_judgments, etc.)
    - q: text search query
    - limit: max results (default 10, max 100)
    - fetch_content: bool - if True, fetches full blob content for each match
    - Dataset-specific filters (year, publisher, status, court, etc.)
    
    Returns matching records with optional full content attached.
    """
    dataset_name = str(params.get("dataset") or "").strip()
    if not dataset_name:
        raise ToolError("MISSING_PARAM", "Parameter 'dataset' is required.")
    
    index_path = DATASET_INDEX_REGISTRY.get(dataset_name)
    if not index_path:
        raise ToolError(
            "INVALID_PARAM",
            f"Unknown dataset '{dataset_name}'. Available: {list(DATASET_INDEX_REGISTRY.keys())}",
        )
    
    q = str(params.get("q") or "").strip().lower()
    limit = params.get("limit")
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, 100))
    
    fetch_content = bool(params.get("fetch_content", False))

    page_id = params.get("pageId")
    if page_id in ("", None):
        page_id = params.get("page_id")
    if page_id in ("", None) and dataset_name == "eli_acts":
        page_id = params.get("ELI") or params.get("eli")
    if page_id is not None:
        page_id = str(page_id).strip()
        if page_id == "":
            page_id = None

    record_index = params.get("recordIndex")
    if record_index in ("", None):
        record_index = params.get("record_index")
    if record_index is not None and record_index != "":
        try:
            record_index = int(record_index)
        except (TypeError, ValueError):
            raise ToolError("VALIDATION_FAILED", "Parameter 'recordIndex' must be an integer.")
    else:
        record_index = None

    if dataset_name == "saos_judgments" and record_index is not None and not page_id:
        raise ToolError(
            "VALIDATION_FAILED",
            "Parameter 'recordIndex' requires 'pageId' for saos_judgments lookups.",
        )
    
    # Read the NDJSON index
    container_client = _connect_container()
    
    try:
        blob_client = container_client.get_blob_client(index_path)
        raw_data = blob_client.download_blob().readall()
        lines = raw_data.decode("utf-8").strip().split("\n")
    except ResourceNotFoundError:
        raise ToolError(
            "NOT_FOUND",
            f"Dataset index not found at {index_path}. Please build the index first.",
        )
    except AzureError as exc:
        logging.exception(f"query_dataset: failed to read index for {dataset_name}")
        raise ToolError(
            "UPSTREAM_ERROR",
            f"Unable to read dataset index for {dataset_name}.",
            {"detail": str(exc)},
            status=502,
        )
    
    # Apply dataset-specific filtering
    results: List[Dict[str, Any]] = []
    total_scanned = 0
    
    for line in lines:
        if not line.strip():
            continue
        total_scanned += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        # Apply filters based on dataset type
        if not _matches_filters(record, params, dataset_name):
            continue

        # Deterministic index lookup (preferred for E2E confirmations).
        if page_id or record_index is not None:
            if dataset_name == "eli_acts":
                # ELI uses ELI identifier (e.g., DU/2025/1882) and pos.
                if page_id and str(record.get("ELI") or "").strip() != page_id:
                    continue
                if record_index is not None and record.get("pos") != record_index:
                    continue
            elif dataset_name == "saos_judgments":
                if page_id and str(record.get("pageId") or "").strip() != page_id:
                    continue
                if record_index is not None and record.get("recordIndex") != record_index:
                    continue

        # Text search across relevant fields
        if q and not _text_search_match(record, q, dataset_name):
            continue
        
        results.append(record)
        
        if len(results) >= limit:
            break
    
    # Optionally fetch full content for matched records
    if fetch_content:
        results = _attach_full_content(results, container_client, dataset_name)
        if dataset_name == "eli_acts":
            response_warning = (
                "ELI dataset currently returns metadata only; full act text is not stored in blob yet."
            )
        else:
            response_warning = None
    else:
        response_warning = None
    
    response = {
        "status": "success",
        "dataset": dataset_name,
        "total_scanned": total_scanned,
        "total_returned": len(results),
        "limit": limit,
        "hits": results,
        "fetch_content": fetch_content,
        "provenance": {
            "index_path": index_path,
        },
    }
    if response_warning:
        response["warning"] = response_warning
    return _apply_response_soft_cap(response)


def _matches_filters(record: Dict, params: Dict, dataset_name: str) -> bool:
    """Apply dataset-specific filters."""
    if dataset_name == "eli_acts":
        # ELI-specific filters
        year = params.get("year")
        if year is not None:
            try:
                if record.get("year") != int(year):
                    return False
            except (TypeError, ValueError):
                return False
        
        publisher = str(params.get("publisher") or "").strip().upper()
        if publisher and record.get("publisher", "").upper() != publisher:
            return False
        
        status = str(params.get("status") or "").strip().lower()
        if status and record.get("status", "").lower() != status:
            return False
    
    elif dataset_name == "saos_judgments":
        # SAOS-specific filters
        court = str(params.get("court") or "").strip().lower()
        if court and court not in record.get("court", "").lower():
            return False
        
        court_type = str(params.get("court_type") or "").strip().lower()
        if court_type and court_type != record.get("courtType", "").lower():
            return False
    
    return True


def _text_search_match(record: Dict, query: str, dataset_name: str) -> bool:
    """Check if record matches text search query."""
    if dataset_name == "eli_acts":
        searchable = " ".join(
            [
                str(record.get("title") or ""),
                str(record.get("displayAddress") or ""),
                str(record.get("ELI") or ""),
                str(record.get("address") or ""),
                str(record.get("type") or ""),
            ]
        ).lower()
        return query in searchable

    elif dataset_name == "saos_judgments":
        # Search in summary, caseNumber, and court name
        searchable = " ".join(
            [
                str(record.get("summary") or ""),
                str(record.get("caseNumber") or ""),
                str(record.get("court") or ""),
            ]
        ).lower()
        return query in searchable
    
    return False


def _attach_full_content(
    results: List[Dict],
    container_client,
    dataset_name: str,
    max_content_bytes: int = QUERY_DATASET_CONTENT_SOFT_CAP,
) -> List[Dict]:
    """Fetch and attach full blob content for each matched record."""
    enriched = []
    
    for record in results:
        # Determine blob path based on dataset structure
        if dataset_name == "saos_judgments":
            page_id = record.get("pageId", "")
            if not page_id:
                enriched.append(record)
                continue
            
            blob_path = f"datasets/saos/judgments/pages/{page_id}.json"
            record_index = record.get("recordIndex", 0)
            
            try:
                blob_client = container_client.get_blob_client(blob_path)
                raw_data = blob_client.download_blob().readall()
                page_data = json.loads(raw_data.decode("utf-8"))
                
                if isinstance(page_data, list) and record_index < len(page_data):
                    candidate = page_data[record_index]
                    content_size = _estimate_json_bytes(candidate)
                    if max_content_bytes and content_size > max_content_bytes:
                        record["_contentTruncated"] = True
                    else:
                        record["_fullContent"] = candidate
            except Exception as e:
                logging.warning(f"Could not fetch content for {blob_path}: {e}")
                record["_contentError"] = str(e)
        
        enriched.append(record)
    
    return enriched


def eli_acts_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query the public ELI acts dataset stored in users/public/datasets/eli_acts/index/acts_inforce_1.jsonl.
    
    **DEPRECATED**: Use query_dataset with dataset="eli_acts" instead.
    This function is kept for backward compatibility.
    
    Supports filters: q (title search), year, publisher, status, limit.
    Returns matching ActInfo records with ELI, title, status, dates, etc.
    """
    # Delegate to unified query_dataset
    params_copy = dict(params)
    params_copy["dataset"] = "eli_acts"
    result = query_dataset(params_copy)
    
    # Maintain old response format for compatibility
    result["provenance"]["source"] = "https://api.sejm.gov.pl/eli/acts/search"
    return result

