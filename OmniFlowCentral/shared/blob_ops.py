"""
Shared blob utilities for App2 tooling.
"""
import json
import logging
import time
from typing import Dict, List, Optional, Tuple

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import ContainerClient

from .config import AzureConfig


class ToolError(Exception):
    def __init__(self, code: str, message: str, details: Optional[Dict] = None, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.status = status


USER_PREFIX = "users"
DEFAULT_MAX_RESULTS = 200
MAX_RESULTS_LIMIT = 1000
DEFAULT_TIMEOUT_SECONDS = 10
MAX_SUFFIX_SCAN = 2000
MAX_SUFFIX_CANDIDATES = 25
DEFAULT_READ_MANY_FILES = 25
DEFAULT_TAIL_BYTES = 65536
DEFAULT_TAIL_LINES = 0
DEFAULT_MAX_BYTES_PER_FILE = 262144


def _get_container_client() -> ContainerClient:
    if not AzureConfig.CONNECTION_STRING:
        raise ToolError("UPSTREAM_ERROR", "Missing Azure storage connection string.")
    try:
        return ContainerClient.from_connection_string(
            AzureConfig.CONNECTION_STRING,
            container_name=AzureConfig.CONTAINER_NAME,
        )
    except Exception as exc:
        logging.exception("Failed to create container client.")
        raise ToolError("UPSTREAM_ERROR", "Storage initialization failed.", {"detail": str(exc)}, 502) from exc


def _user_blob_prefix(user_id: str) -> str:
    normalized = user_id.strip().replace("/", "_").replace("\\", "_") or "default"
    return f"{USER_PREFIX}/{normalized}"


def _apply_user_prefix(name: str, user_id: str) -> str:
    sanitized = name.strip().lstrip("/")
    prefix = _user_blob_prefix(user_id)
    if sanitized.startswith(prefix + "/"):
        return sanitized
    return f"{prefix}/{sanitized}"


def _strip_user_prefix(name: str, user_id: str) -> str:
    prefix = f"{_user_blob_prefix(user_id)}/"
    if name.startswith(prefix):
        return name[len(prefix) :]
    return name


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_tail_lines(blob_client, *, tail_lines: int, tail_bytes: int):
    props = blob_client.get_blob_properties()
    size = int(getattr(props, "size", 0) or 0)
    if size <= 0:
        return "", False, 0
    length = min(size, max(1, tail_bytes))
    offset = max(0, size - length)
    raw = blob_client.download_blob(offset=offset, length=length).readall()
    text = raw.decode("utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if tail_lines > 0:
        lines = lines[-tail_lines:]
    return "\n".join(lines), offset > 0, len(raw)


def _read_prefix(blob_client, *, max_bytes: int):
    props = blob_client.get_blob_properties()
    size = int(getattr(props, "size", 0) or 0)
    if size <= 0:
        return b"", False
    if max_bytes <= 0 or size <= max_bytes:
        data = blob_client.download_blob().readall()
        return data, False
    data = blob_client.download_blob(offset=0, length=max_bytes).readall()
    return data, True


def _is_basename_only(value: str) -> bool:
    val = value.strip()
    return bool(val) and ("/" not in val) and ("\\" not in val)


def _try_unique_suffix_resolve(
    container: ContainerClient, *, user_id: str, file_name: str, max_scan: int = MAX_SUFFIX_SCAN
) -> Tuple[Optional[str], List[str]]:
    prefix = f"{_user_blob_prefix(user_id)}/"
    suffix = f"/{file_name}"
    candidates: List[str] = []
    scanned = 0
    try:
        iterator = container.list_blobs(name_starts_with=prefix)
    except AzureError as exc:
        logging.warning("Suffix resolve failed: %s", exc)
        return None, []
    for blob in iterator:
        scanned += 1
        if scanned > max_scan:
            break
        name = getattr(blob, "name", "") or ""
        if not name.endswith(suffix):
            continue
        rel = name[len(prefix) :]
        if rel:
            candidates.append(rel)
            if len(candidates) >= MAX_SUFFIX_CANDIDATES:
                break
    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


def _download_blob(
    container: ContainerClient,
    blob_name: str,
    user_id: str,
    requested_name: Optional[str] = None,
    resolved: bool = False,
) -> Dict[str, object]:
    blob_client = container.get_blob_client(blob_name)
    data = blob_client.download_blob().readall()
    text = data.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
        content_type = "json"
        payload = parsed
    except json.JSONDecodeError:
        content_type = "text"
        payload = text
    return {
        "file_name": _strip_user_prefix(blob_name, user_id),
        "requested_file_name": requested_name,
        "resolved": resolved,
        "data": payload,
        "content_type": content_type,
        "size": len(data),
    }


def list_blobs(
    user_id: str,
    prefix: Optional[str] = None,
    max_results: int = DEFAULT_MAX_RESULTS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> List[Dict[str, Optional[str]]]:
    container = _get_container_client()
    trimmed_prefix = prefix.strip() if prefix else ""
    full_prefix = (
        f"{_user_blob_prefix(user_id)}/{trimmed_prefix}"
        if trimmed_prefix
        else f"{_user_blob_prefix(user_id)}/"
    )

    max_results = max(0, min(max_results, MAX_RESULTS_LIMIT))
    timeout_seconds = max(1, min(timeout_seconds, 60))

    blobs = []
    start = time.monotonic()
    try:
        for blob in container.list_blobs(name_starts_with=full_prefix, timeout=timeout_seconds):
            blobs.append(
                {
                    "name": _strip_user_prefix(blob.name, user_id),
                    "size": getattr(blob, "size", None),
                    "last_modified": getattr(blob, "last_modified", None).isoformat()
                    if getattr(blob, "last_modified", None)
                    else None,
                }
            )
            if len(blobs) >= max_results:
                break
            if time.monotonic() - start > timeout_seconds:
                break
    except Exception as exc:
        logging.exception("Error listing blobs")
        raise ToolError("UPSTREAM_ERROR", "Unable to list blobs.", {"detail": str(exc)})

    return blobs


def upload_blob(name: str, content: str, user_id: str, overwrite: bool = True) -> Dict[str, object]:
    if not name:
        raise ToolError("MISSING_PARAM", "Missing blob name.")
    if content is None:
        raise ToolError("MISSING_PARAM", "Missing content.")

    blob_name = _apply_user_prefix(name, user_id)
    container = _get_container_client()
    blob_client = container.get_blob_client(blob_name)
    try:
        payload = content.encode("utf-8") if isinstance(content, str) else content
        blob_client.upload_blob(payload, overwrite=overwrite)
        return {
            "name": _strip_user_prefix(blob_name, user_id),
            "size": len(payload),
            "status": "uploaded",
        }
    except Exception as exc:
        logging.exception("Error uploading blob")
        raise ToolError("UPSTREAM_ERROR", "Unable to upload blob.", {"detail": str(exc)})


def delete_blob(name: str, user_id: str) -> Dict[str, object]:
    if not name:
        raise ToolError("MISSING_PARAM", "Missing blob name.")

    blob_name = _apply_user_prefix(name, user_id)
    container = _get_container_client()
    blob_client = container.get_blob_client(blob_name)
    try:
        blob_client.delete_blob()
        return {"name": _strip_user_prefix(blob_name, user_id), "status": "deleted"}
    except Exception as exc:
        logging.exception("Error deleting blob")
        raise ToolError("UPSTREAM_ERROR", "Unable to delete blob.", {"detail": str(exc)})


def read_blob(user_id: str, name: str) -> Dict[str, object]:
    sanitized = (name or "").strip()
    if not sanitized:
        raise ToolError("MISSING_PARAM", "Missing blob name.")

    container = _get_container_client()
    blob_name = _apply_user_prefix(sanitized, user_id)
    try:
        return _download_blob(container, blob_name, user_id, requested_name=sanitized)
    except ResourceNotFoundError:
        if _is_basename_only(sanitized):
            resolved, candidates = _try_unique_suffix_resolve(container, user_id=user_id, file_name=sanitized)
            if resolved:
                return _download_blob(
                    container,
                    f"{_user_blob_prefix(user_id)}/{resolved}",
                    user_id,
                    requested_name=sanitized,
                    resolved=True,
                )
            if candidates:
                raise ToolError(
                    "VALIDATION_FAILED",
                    "Basename ambiguous; multiple candidates found.",
                    {"candidates": candidates[:MAX_SUFFIX_CANDIDATES]},
                    status=404,
                )
        raise ToolError("MISSING_PARAM", f"File '{sanitized}' not found.", status=404)
    except AzureError as exc:
        logging.exception("Error reading blob")
        raise ToolError("UPSTREAM_ERROR", "Unable to read blob.", {"detail": str(exc)}, status=502)


def _normalize_entries(data: object) -> object:
    if isinstance(data, list):
        normalized = []
        for entry in data:
            if isinstance(entry, str):
                try:
                    normalized.append(json.loads(entry))
                except Exception:
                    normalized.append({"_raw": entry})
            else:
                normalized.append(entry)
        return normalized
    return data


def get_filtered_data(
    user_id: str,
    blob_name: str,
    filter_key: Optional[str] = None,
    filter_value: Optional[str] = None,
) -> Dict[str, object]:
    sanitized = (blob_name or "").strip()
    if not sanitized:
        raise ToolError("MISSING_PARAM", "Missing blob name.")
    container = _get_container_client()
    blob_client = container.get_blob_client(_apply_user_prefix(sanitized, user_id))
    try:
        raw = blob_client.download_blob().readall().decode("utf-8")
        parsed = json.loads(raw)
    except ResourceNotFoundError as exc:
        raise ToolError("MISSING_PARAM", f"File '{sanitized}' not found.", status=404) from exc
    except json.JSONDecodeError as exc:
        raise ToolError("UPSTREAM_ERROR", "Invalid JSON format.", {"detail": str(exc)}, status=500) from exc
    except AzureError as exc:
        logging.exception("Error reading blob for filtering")
        raise ToolError("UPSTREAM_ERROR", "Unable to read blob.", {"detail": str(exc)}, status=502) from exc

    normalized = _normalize_entries(parsed)
    total = len(normalized) if isinstance(normalized, list) else 1
    filtered = normalized
    if filter_key and filter_value is not None and isinstance(normalized, list):
        filtered = [
            entry
            for entry in normalized
            if isinstance(entry, dict) and str(entry.get(filter_key)) == str(filter_value)
        ]

    response = {
        "status": "success",
        "user_id": user_id,
        "file": sanitized,
        "filter": {"key": filter_key, "value": filter_value} if filter_key and filter_value is not None else None,
        "data": filtered,
        "count": len(filtered) if isinstance(filtered, list) else 1,
        "total": total,
    }
    return response


def read_many_blobs(
    user_id: str,
    files: List[str],
    tail_lines: int = DEFAULT_TAIL_LINES,
    tail_bytes: int = DEFAULT_TAIL_BYTES,
    max_bytes_per_file: int = DEFAULT_MAX_BYTES_PER_FILE,
    parse_json: bool = True,
    max_files: int = DEFAULT_READ_MANY_FILES,
) -> Dict[str, object]:
    trimmed_files = []
    if not isinstance(files, list) or not files:
        raise ToolError("VALIDATION_FAILED", "Field 'files' must be a non-empty array of strings.")
    for raw in files:
        if not isinstance(raw, str):
            raise ToolError("VALIDATION_FAILED", "Each file name must be a non-empty string.")
        candidate = raw.strip()
        if not candidate:
            raise ToolError("VALIDATION_FAILED", "Each file name must be a non-empty string.")
        trimmed_files.append(candidate)

    if max_files <= 0:
        max_files = DEFAULT_READ_MANY_FILES
    if len(trimmed_files) > max_files:
        raise ToolError("VALIDATION_FAILED", f"Too many files (max {max_files}).")

    container = _get_container_client()
    items = []
    errors = 0
    total_bytes = 0
    tail_lines = max(0, tail_lines)
    tail_bytes = max(0, tail_bytes)

    for file_name in trimmed_files:
        blob_name = _apply_user_prefix(file_name, user_id)
        blob_client = container.get_blob_client(blob_name)
        try:
            if tail_lines > 0:
                text, truncated, bytes_read = _read_tail_lines(
                    blob_client, tail_lines=tail_lines, tail_bytes=tail_bytes
                )
                total_bytes += bytes_read
                items.append(
                    {
                        "file_name": file_name,
                        "content_type": "text",
                        "data": text,
                        "bytes": bytes_read,
                        "truncated": truncated,
                        "mode": "tail",
                    }
                )
                continue

            data, truncated = _read_prefix(blob_client, max_bytes=max_bytes_per_file)
            total_bytes += len(data)
            if parse_json:
                try:
                    parsed = json.loads(data.decode("utf-8"))
                    items.append(
                        {
                            "file_name": file_name,
                            "content_type": "json",
                            "data": parsed,
                            "bytes": len(data),
                            "truncated": truncated,
                            "mode": "read",
                        }
                    )
                    continue
                except Exception:
                    pass

            items.append(
                {
                    "file_name": file_name,
                    "content_type": "text",
                    "data": data.decode("utf-8", errors="replace"),
                    "bytes": len(data),
                    "truncated": truncated,
                    "mode": "read",
                }
            )
        except ResourceNotFoundError:
            errors += 1
            items.append({"file_name": file_name, "error": "not_found"})
        except AzureError as exc:
            errors += 1
            items.append({"file_name": file_name, "error": f"azure_error: {str(exc)}"})
        except Exception as exc:
            errors += 1
            items.append({"file_name": file_name, "error": f"unexpected_error: {str(exc)}"})

    return {
        "items": items,
        "count": len(items),
        "errors": errors,
        "total_bytes": total_bytes,
    }
