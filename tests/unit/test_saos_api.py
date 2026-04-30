from unittest.mock import Mock, patch

import pytest
import requests

from OmniFlowCentral.shared.blob_ops import ToolError
from OmniFlowCentral.shared.saos_api import saos_detail, saos_search


def _response(payload, status_code=200):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = payload
    return resp


def test_saos_search_normalizes_hits_and_query_params():
    payload = {
        "totalResults": 1,
        "items": [
            {
                "id": 123,
                "href": "https://www.saos.org.pl/api/judgments/123",
                "courtType": "COMMON",
                "judgmentType": "SENTENCE",
                "judgmentDate": "2025-01-02",
                "courtCases": [{"caseNumber": "I ACa 1/25"}],
                "division": {"court": {"name": "Sąd Apelacyjny w Warszawie"}},
                "textContent": "...przedawnienie...",
            }
        ],
    }
    with patch("OmniFlowCentral.shared.saos_api.requests.get", return_value=_response(payload)) as get:
        result = saos_search(
            {
                "q": "przedawnienie",
                "limit": 5,
                "page": 1,
                "court_type": "common",
                "judgment_date_from": "2025-01-01",
                "case_number": "I ACa 1/25",
            }
        )

    assert result["status"] == "success"
    assert result["total_returned"] == 1
    hit = result["hits"][0]
    assert hit["judgment_id"] == 123
    assert hit["case_number"] == "I ACa 1/25"
    assert hit["court"] == "Sąd Apelacyjny w Warszawie"
    assert hit["url"] == "https://www.saos.org.pl/judgments/123"
    params = get.call_args.kwargs["params"]
    assert params["all"] == "przedawnienie"
    assert params["pageNumber"] == 1
    assert params["courtType"] == "COMMON"
    assert params["judgmentDateFrom"] == "2025-01-01"
    assert params["caseNumber"] == "I ACa 1/25"


def test_saos_detail_returns_normalized_judgment():
    payload = {
        "id": 123,
        "href": "https://www.saos.org.pl/api/judgments/123",
        "courtType": "COMMON",
        "judgmentDate": "2025-01-02",
        "courtCases": [{"caseNumber": "I ACa 1/25"}],
        "division": {"court": {"name": "Sąd Apelacyjny w Warszawie"}},
        "textContent": "Pełny tekst",
        "legalBases": ["art. 118 k.c."],
        "referencedRegulations": [{"journalYear": 1964, "journalEntry": 93}],
    }
    with patch("OmniFlowCentral.shared.saos_api.requests.get", return_value=_response(payload)):
        result = saos_detail({"judgment_id": "123"})

    assert result["status"] == "success"
    assert result["judgment_id"] == 123
    judgment = result["judgment"]
    assert judgment["case_number"] == "I ACa 1/25"
    assert judgment["legal_bases"] == ["art. 118 k.c."]
    assert judgment["referenced_regulations"][0]["journalYear"] == 1964
    assert judgment["textContent"] == "Pełny tekst"


def test_saos_detail_validates_judgment_id():
    with pytest.raises(ToolError) as exc:
        saos_detail({"judgment_id": "abc"})
    assert exc.value.code == "VALIDATION_FAILED"


def test_saos_api_timeout_maps_to_tool_error():
    with patch("OmniFlowCentral.shared.saos_api.requests.get", side_effect=requests.Timeout()):
        with pytest.raises(ToolError) as exc:
            saos_search({"q": "test"})
    assert exc.value.code == "UPSTREAM_TIMEOUT"
    assert exc.value.status == 504
