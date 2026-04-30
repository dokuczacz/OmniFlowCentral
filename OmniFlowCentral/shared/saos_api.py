from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from .blob_ops import ToolError


SAOS_BASE_URL = "https://www.saos.org.pl/api"
SAOS_SEARCH_URL = f"{SAOS_BASE_URL}/search/judgments"
SAOS_DETAIL_URL = f"{SAOS_BASE_URL}/judgments"
SAOS_DEFAULT_TIMEOUT = 15.0
SAOS_DEFAULT_LIMIT = 10
SAOS_MAX_LIMIT = 100
SAOS_DETAIL_TEXT_MAX_CHARS = 50_000


def _parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _request_json(url: str, *, params: Optional[Dict[str, Any]] = None, timeout: float = SAOS_DEFAULT_TIMEOUT) -> Dict[str, Any]:
    if not url.startswith(SAOS_BASE_URL + "/"):
        raise ToolError("VALIDATION_FAILED", "SAOS URL is outside the allowed API host.")

    try:
        response = requests.get(url, params=params, timeout=timeout, headers={"Accept": "application/json"})
    except requests.Timeout as exc:
        raise ToolError("UPSTREAM_TIMEOUT", "SAOS API request timed out.", status=504) from exc
    except requests.RequestException as exc:
        logging.warning("SAOS API request failed: %s", exc)
        raise ToolError("UPSTREAM_ERROR", "SAOS API request failed.", {"detail": str(exc)}, status=502) from exc

    if response.status_code == 404:
        raise ToolError("NOT_FOUND", "SAOS judgment not found.", status=404)
    if response.status_code >= 400:
        raise ToolError(
            "UPSTREAM_ERROR",
            "SAOS API returned an error.",
            {"status_code": response.status_code},
            status=502,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise ToolError("UPSTREAM_ERROR", "SAOS API returned non-JSON response.", status=502) from exc
    if not isinstance(payload, dict):
        raise ToolError("UPSTREAM_ERROR", "SAOS API returned unexpected response shape.", status=502)
    return payload


def _first_case_number(record: Dict[str, Any]) -> Optional[str]:
    cases = record.get("courtCases")
    if isinstance(cases, list):
        for case in cases:
            if isinstance(case, dict):
                number = _clean_string(case.get("caseNumber"))
                if number:
                    return number
    return None


def _court_name(record: Dict[str, Any]) -> Optional[str]:
    division = record.get("division")
    if isinstance(division, dict):
        court = division.get("court")
        if isinstance(court, dict):
            name = _clean_string(court.get("name"))
            if name:
                return name
        name = _clean_string(division.get("name"))
        if name:
            return name
    return _clean_string(record.get("courtName"))


def _normalize_judgment_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    judgment_id = record.get("id")
    href = _clean_string(record.get("href")) or (f"{SAOS_DETAIL_URL}/{judgment_id}" if judgment_id else None)
    return {
        "id": judgment_id,
        "judgment_id": judgment_id,
        "case_number": _first_case_number(record),
        "court": _court_name(record),
        "court_type": record.get("courtType"),
        "judgment_type": record.get("judgmentType"),
        "judgment_date": record.get("judgmentDate"),
        "href": href,
        "url": f"https://www.saos.org.pl/judgments/{judgment_id}" if judgment_id else None,
        "snippet": record.get("textContent"),
        "keywords": record.get("keywords") or [],
        "source": {
            "name": "SAOS",
            "api": href,
            "ui": f"https://www.saos.org.pl/judgments/{judgment_id}" if judgment_id else None,
        },
        "raw": record,
    }


def _normalize_judgment_detail(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_judgment_summary(record)
    text = record.get("textContent")
    if isinstance(text, str) and len(text) > SAOS_DETAIL_TEXT_MAX_CHARS:
        normalized["textContent"] = text[:SAOS_DETAIL_TEXT_MAX_CHARS]
        normalized["_textContentTruncated"] = True
        normalized["_textContentLength"] = len(text)
    else:
        normalized["textContent"] = text
        normalized["_textContentTruncated"] = False
    normalized.update(
        {
            "summary": record.get("summary"),
            "decision": record.get("decision"),
            "legal_bases": record.get("legalBases") or [],
            "referenced_regulations": record.get("referencedRegulations") or [],
            "judges": record.get("judges") or [],
            "referenced_court_cases": record.get("referencedCourtCases") or [],
            "source_details": record.get("source") or {},
        }
    )
    return normalized


def saos_search(params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    limit = max(1, min(_parse_int(params.get("limit"), SAOS_DEFAULT_LIMIT), SAOS_MAX_LIMIT))
    page = max(0, _parse_int(params.get("page"), 0))
    page_size = params.get("page_size")
    if page_size is None:
        page_size = max(10, limit)
    page_size = max(10, min(_parse_int(page_size, max(10, limit)), SAOS_MAX_LIMIT))

    query_params: Dict[str, Any] = {
        "pageSize": page_size,
        "pageNumber": page,
        "sortingField": "JUDGMENT_DATE",
        "sortingDirection": "DESC",
    }
    mappings = {
        "q": "all",
        "court_type": "courtType",
        "judgment_date_from": "judgmentDateFrom",
        "judgment_date_to": "judgmentDateTo",
        "case_number": "caseNumber",
    }
    for source, target in mappings.items():
        value = _clean_string(params.get(source))
        if value:
            query_params[target] = value.upper() if source == "court_type" else value

    payload = _request_json(SAOS_SEARCH_URL, params=query_params)
    raw_items = payload.get("items") or []
    if not isinstance(raw_items, list):
        raw_items = []
    hits: List[Dict[str, Any]] = [
        _normalize_judgment_summary(item)
        for item in raw_items[:limit]
        if isinstance(item, dict)
    ]
    return {
        "status": "success",
        "source": "saos",
        "query": query_params,
        "page": page,
        "page_size": page_size,
        "limit": limit,
        "total_returned": len(hits),
        "total_available": payload.get("totalResults") or payload.get("totalCount"),
        "hits": hits,
        "provenance": {"api_url": SAOS_SEARCH_URL},
    }


def saos_detail(params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    judgment_id = _clean_string(params.get("judgment_id") or params.get("id"))
    if not judgment_id:
        raise ToolError("MISSING_PARAM", "Parameter 'judgment_id' is required.")
    if not judgment_id.isdigit():
        raise ToolError("VALIDATION_FAILED", "Parameter 'judgment_id' must be a positive integer.")

    url = f"{SAOS_DETAIL_URL}/{judgment_id}"
    payload = _request_json(url)
    record = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(record, dict):
        raise ToolError("UPSTREAM_ERROR", "SAOS detail response has unexpected shape.", status=502)
    return {
        "status": "success",
        "source": "saos",
        "judgment_id": int(judgment_id),
        "judgment": _normalize_judgment_detail(record),
        "provenance": {"api_url": url},
    }
