"""
Shared blob utilities for App2 tooling.
"""
import logging
import time
from typing import Dict, List, Optional

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
