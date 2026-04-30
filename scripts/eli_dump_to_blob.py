import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from OmniFlowCentral.shared.blob_ops import ToolError, upload_blob
from OmniFlowCentral.shared.config import AzureConfig


ELI_BASE_URL = "https://api.sejm.gov.pl/eli"


def _ensure_container_exists(*, connection_string: str, container_name: str) -> None:
    if not connection_string or not container_name:
        raise ToolError(
            "UPSTREAM_ERROR",
            "Missing Azure storage configuration for container initialization.",
        )
    service = BlobServiceClient.from_connection_string(connection_string)
    try:
        service.create_container(container_name)
    except ResourceExistsError:
        return


def _parse_kv_pairs(pairs: Iterable[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for raw in pairs:
        if "=" not in raw:
            raise ValueError(f"Expected KEY=VALUE, got {raw!r}")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty key in {raw!r}")
        params[key] = value.strip()
    return params


def _fetch_acts_page(*, offset: int, limit: int, params: Dict[str, str], timeout_seconds: float) -> Dict:
    query = dict(params)
    query.update({"offset": offset, "limit": limit})
    resp = requests.get(f"{ELI_BASE_URL}/acts/search", params=query, timeout=timeout_seconds)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError("Unexpected response: expected JSON object")
    return data


def _fetch_changed_acts_page(*, since: str, offset: int, limit: int, timeout_seconds: float) -> Dict:
    resp = requests.get(
        f"{ELI_BASE_URL}/changes/acts",
        params={"since": since, "offset": offset, "limit": limit},
        timeout=timeout_seconds,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError("Unexpected changes response: expected JSON object")
    return data


def _fetch_act_details(*, eli_id: str, timeout_seconds: float) -> Dict:
    resp = requests.get(f"{ELI_BASE_URL}/acts/{eli_id}", timeout=timeout_seconds)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected act details response for {eli_id}: expected JSON object")
    data.setdefault("ELI", eli_id)
    data.setdefault("pageId", eli_id)
    return data


def _extract_changed_eli_ids(payload: Dict) -> List[str]:
    found: List[str] = []

    def walk(value) -> None:
        if isinstance(value, dict):
            publisher = str(value.get("publisher") or value.get("Publisher") or "").strip().upper()
            year = value.get("year") or value.get("Year")
            pos = value.get("pos") or value.get("position") or value.get("Position")
            if publisher in {"DU", "MP"} and year and pos:
                try:
                    found.append(f"{publisher}/{int(year)}/{int(pos)}")
                except (TypeError, ValueError):
                    pass
            for key in ("ELI", "eli", "pageId", "actId", "id"):
                raw = value.get(key)
                if isinstance(raw, str) and raw.count("/") == 2:
                    prefix = raw.split("/", 1)[0].upper()
                    if prefix in {"DU", "MP"}:
                        found.append(raw.strip())
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    deduped: List[str] = []
    seen = set()
    for eli_id in found:
        if eli_id not in seen:
            seen.add(eli_id)
            deduped.append(eli_id)
    return deduped


def _download_index_records(*, connection_string: str, container_name: str, index_blob: str) -> Dict[str, Dict]:
    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client(container_name)
    try:
        raw = container.get_blob_client(index_blob).download_blob().readall()
    except ResourceNotFoundError:
        return {}

    records: Dict[str, Dict] = {}
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        eli_id = str(record.get("ELI") or record.get("pageId") or "").strip()
        if eli_id:
            records[eli_id] = record
    return records


def _is_development_storage(connection_string: str) -> bool:
    return connection_string.strip().lower() == "usedevelopmentstorage=true"


def _extract_paging(payload: Dict) -> Tuple[int, int, int]:
    try:
        offset = int(payload.get("offset", 0))
        count = int(payload.get("count", 0))
        total = int(payload.get("totalCount", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Unexpected paging fields in response") from exc
    return offset, count, total


def _list_page_blobs(
    *, connection_string: str, container_name: str, user_id: str, blob_prefix: str
) -> List[str]:
    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client(container_name)
    prefix = f"users/{user_id}/{blob_prefix.rstrip('/')}/pages/"
    names = [b.name for b in container.list_blobs(name_starts_with=prefix)]     
    return sorted(names)


def _download_json_blob(*, connection_string: str, container_name: str, blob_name: str) -> Dict:
    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client(container_name)
    raw = container.get_blob_client(blob_name).download_blob().readall()        
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Unexpected stored page payload (expected object)")    
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch pages from Sejm ELI /acts/search and store them in OmniFlowCentral blob storage."
    )
    parser.add_argument(
        "--user-id",
        default="public",
        help="Storage namespace under users/{user_id}/ (default: public).",     
    )
    parser.add_argument(
        "--connection-string",
        default="",
        help="Override storage connection string (otherwise uses environment / AzureConfig).",
    )
    parser.add_argument(
        "--container-name",
        default="",
        help="Override container name (otherwise uses environment / AzureConfig).",
    )
    parser.add_argument(
        "--blob-prefix",
        default="datasets/eli_acts",
        help="Blob folder to write into under users/{user_id}/ (default: datasets/eli_acts).",
    )
    parser.add_argument("--offset", type=int, default=0, help="Start offset (default: 0).")
    parser.add_argument("--limit", type=int, default=500, help="Page size (default: 500).")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="How many pages to fetch (default: 1). Use -1 to fetch until the API reports completion.",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Extra query parameter for /acts/search as KEY=VALUE (repeatable).",
    )
    parser.add_argument(
        "--write-index-jsonl",
        action="store_true",
        help="Also write a compact JSONL index of all ActInfo items for this run.",
    )
    parser.add_argument(
        "--build-index-from-blob",
        action="store_true",
        help="Do not fetch from ELI; instead build index + run metadata from already-uploaded pages in blob.",
    )
    parser.add_argument(
        "--changed-since",
        default="",
        help="Delta refresh mode: fetch ELI changed acts since YYYY-MM-DD, merge into the current Azure index, and write the refreshed JSONL index.",
    )
    parser.add_argument(
        "--require-azure-storage",
        action="store_true",
        help="Fail fast when storage resolves to Azurite/development storage. Use for production ELI refresh runs.",
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.2, help="Delay between pages (default: 0.2).")
    parser.add_argument("--timeout-seconds", type=float, default=20.0, help="HTTP timeout (default: 20).")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not upload to blob.")
    args = parser.parse_args()

    connection_string = (args.connection_string or "").strip() or (AzureConfig.CONNECTION_STRING or "").strip()
    container_name = (args.container_name or "").strip() or (AzureConfig.CONTAINER_NAME or "").strip()
    if not connection_string or not container_name:
        raise ToolError("UPSTREAM_ERROR", "Missing Azure storage configuration.")
    if args.require_azure_storage and _is_development_storage(connection_string):
        raise ToolError(
            "VALIDATION_FAILED",
            "--require-azure-storage was set, but storage is Azurite/development storage.",
        )
    # Ensure shared helpers (upload_blob, manifest updates) use the overridden target.
    AzureConfig.CONNECTION_STRING = connection_string
    AzureConfig.CONTAINER_NAME = container_name

    extra_params = {"inForce": "1"}
    extra_params.update(_parse_kv_pairs(args.param))
    if not args.dry_run:
        _ensure_container_exists(connection_string=connection_string, container_name=container_name)

    pages_fetched = 0
    next_offset = max(0, int(args.offset))
    limit = max(1, int(args.limit))

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_meta = {
        "source": {"base_url": ELI_BASE_URL, "endpoint": "/acts/search"},
        "query": {**extra_params, "limit": limit, "offset": next_offset},
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "pages": [],
    }
    if args.changed_since:
        run_meta["source"]["endpoint"] = "/changes/acts"
        run_meta["query"]["since"] = args.changed_since

    jsonl_tmp = None
    jsonl_count = 0
    jsonl_bytes = 0
    jsonl_hasher = hashlib.sha256()
    try:
        if args.write_index_jsonl:
            jsonl_tmp = tempfile.NamedTemporaryFile(mode="wb", delete=False)

        if args.changed_since:
            if not args.write_index_jsonl:
                raise ValueError("--changed-since requires --write-index-jsonl")

            index_blob_abs = f"users/{args.user_id}/{args.blob_prefix.rstrip('/')}/index/acts_inforce_1.jsonl"
            index_records = _download_index_records(
                connection_string=connection_string,
                container_name=container_name,
                index_blob=index_blob_abs,
            )
            existing_count_before_merge = len(index_records)
            changed_ids: List[str] = []

            while True:
                if args.max_pages >= 0 and pages_fetched >= args.max_pages:
                    break

                page = _fetch_changed_acts_page(
                    since=args.changed_since,
                    offset=next_offset,
                    limit=limit,
                    timeout_seconds=float(args.timeout_seconds),
                )
                page_offset, page_count, total = _extract_paging(page)
                page_ids = _extract_changed_eli_ids(page)
                changed_ids.extend(page_ids)

                blob_name = (
                    f"{args.blob_prefix.rstrip('/')}/changes/"
                    f"changes_since_{args.changed_since}_offset_{page_offset:09}.json"
                )
                payload = json.dumps(page, ensure_ascii=False, separators=(",", ":"))
                if not args.dry_run:
                    upload_blob(
                        name=blob_name,
                        content=payload,
                        user_id=args.user_id,
                        overwrite=True,
                    )

                run_meta["pages"].append(
                    {
                        "blob_name": blob_name,
                        "offset": page_offset,
                        "count": page_count,
                        "totalCount": total,
                        "changed_eli_ids": len(page_ids),
                    }
                )
                pages_fetched += 1
                if page_count <= 0:
                    break
                next_offset = page_offset + page_count
                if total and next_offset >= total:
                    break
                if args.sleep_seconds > 0:
                    time.sleep(float(args.sleep_seconds))

            unique_changed_ids = sorted(set(changed_ids))
            for eli_id in unique_changed_ids:
                detail = _fetch_act_details(eli_id=eli_id, timeout_seconds=float(args.timeout_seconds))
                index_records[eli_id] = detail

            if jsonl_tmp is not None:
                for eli_id in sorted(index_records):
                    line = json.dumps(index_records[eli_id], ensure_ascii=False, separators=(",", ":")) + "\n"
                    raw = line.encode("utf-8")
                    jsonl_tmp.write(raw)
                    jsonl_hasher.update(raw)
                    jsonl_count += 1
                    jsonl_bytes += len(raw)

            run_meta["delta"] = {
                "changed_since": args.changed_since,
                "changed_eli_ids": unique_changed_ids,
                "existing_index_records_before_merge": existing_count_before_merge,
                "index_records_after_merge": len(index_records),
            }
        elif args.build_index_from_blob:
            if not args.write_index_jsonl:
                raise ValueError("--build-index-from-blob requires --write-index-jsonl")
            page_blob_names = _list_page_blobs(
                connection_string=connection_string,
                container_name=container_name,
                user_id=args.user_id,
                blob_prefix=args.blob_prefix,
            )
            if not page_blob_names:
                raise ValueError("No page blobs found to build index from.")    
            total = None
            for name in page_blob_names:
                page = _download_json_blob(
                    connection_string=connection_string,
                    container_name=container_name,
                    blob_name=name,
                )
                page_offset, page_count, page_total = _extract_paging(page)     
                if total is None:
                    total = page_total
                blob_rel = name.split(f"users/{args.user_id}/", 1)[-1]
                run_meta["pages"].append(
                    {
                        "blob_name": blob_rel,
                        "offset": page_offset,
                        "count": page_count,
                        "totalCount": page_total,
                    }
                )
                if jsonl_tmp is not None:
                    for item in page.get("items") or []:
                        line = json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
                        raw = line.encode("utf-8")
                        jsonl_tmp.write(raw)
                        jsonl_hasher.update(raw)
                        jsonl_count += 1
                        jsonl_bytes += len(raw)
                pages_fetched += 1
                next_offset = page_offset + page_count
        else:
            while True:
                if args.max_pages >= 0 and pages_fetched >= args.max_pages:
                    break

                page = _fetch_acts_page(
                    offset=next_offset,
                    limit=limit,
                    params=extra_params,
                    timeout_seconds=float(args.timeout_seconds),
                )
                page_offset, page_count, total = _extract_paging(page)

                blob_name = f"{args.blob_prefix.rstrip('/')}/pages/acts_offset_{page_offset:09}.json"
                payload = json.dumps(page, ensure_ascii=False, separators=(",", ":"))
                if not args.dry_run:
                    upload_blob(
                        name=blob_name,
                        content=payload,
                        user_id=args.user_id,
                        overwrite=True,
                    )

                if jsonl_tmp is not None:
                    for item in page.get("items") or []:
                        line = json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
                        raw = line.encode("utf-8")
                        jsonl_tmp.write(raw)
                        jsonl_hasher.update(raw)
                        jsonl_count += 1
                        jsonl_bytes += len(raw)

                run_meta["pages"].append(
                    {
                        "blob_name": blob_name,
                        "offset": page_offset,
                        "count": page_count,
                        "totalCount": total,
                    }
                )

                pages_fetched += 1
                if page_count <= 0:
                    break
                next_offset = page_offset + page_count
                if total and next_offset >= total:
                    break
                if args.sleep_seconds > 0:
                    time.sleep(float(args.sleep_seconds))
    finally:
        if jsonl_tmp is not None:
            jsonl_tmp.close()

    index_blob = f"{args.blob_prefix.rstrip('/')}/index/acts_inforce_1.jsonl"
    if jsonl_tmp is not None and not args.dry_run:
        with open(jsonl_tmp.name, "rb") as fh:
            upload_blob(
                name=index_blob,
                content=fh.read().decode("utf-8", errors="strict"),
                user_id=args.user_id,
                overwrite=True,
            )

    run_meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    run_meta["checksum"] = {
        "pages_fetched": pages_fetched,
        "last_offset": next_offset,
        "items_jsonl": {
            "enabled": bool(args.write_index_jsonl),
            "blob_name": index_blob if args.write_index_jsonl else None,
            "count": jsonl_count if args.write_index_jsonl else None,
            "size_bytes": jsonl_bytes if args.write_index_jsonl else None,
            "sha256": jsonl_hasher.hexdigest() if args.write_index_jsonl else None,
        },
        "params": extra_params,
        "env": {
            "storage": "azurite"
            if str(os.environ.get("AzureWebJobsStorage", "")).strip().lower() == "usedevelopmentstorage=true"
            else "custom",
            "container": AzureConfig.CONTAINER_NAME,
        },
    }
    run_meta_blob = f"{args.blob_prefix.rstrip('/')}/runs/{run_id}.json"
    if not args.dry_run:
        upload_blob(
            name=run_meta_blob,
            content=json.dumps(run_meta, ensure_ascii=False, separators=(",", ":")),
            user_id=args.user_id,
            overwrite=True,
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "dry_run": bool(args.dry_run),
                "pages_fetched": pages_fetched,
                "last_offset": next_offset,
                "run_meta_blob": run_meta_blob,
                "index_blob": index_blob if args.write_index_jsonl else None,
            },
            ensure_ascii=False,
        )
    )
    if jsonl_tmp is not None:
        try:
            os.unlink(jsonl_tmp.name)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ToolError as exc:
        print(json.dumps({"status": "error", "code": exc.code, "message": exc.message, "details": exc.details}))
        raise SystemExit(2)
