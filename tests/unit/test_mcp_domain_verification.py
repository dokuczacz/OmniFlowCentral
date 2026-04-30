from starlette.testclient import TestClient

from OmniFlowCentral.mcp_app.server import mcp


def test_domain_verification_route_returns_token(monkeypatch):
    monkeypatch.setenv("OPENAI_APPS_DOMAIN_VERIFICATION_TOKEN", "token-123")
    app = mcp.streamable_http_app()
    client = TestClient(app)

    response = client.get("/.well-known/openai-apps-domain-verification")
    assert response.status_code == 200
    assert response.text == "token-123"


def test_domain_verification_route_requires_configured_token(monkeypatch):
    monkeypatch.delenv("OPENAI_APPS_DOMAIN_VERIFICATION_TOKEN", raising=False)
    app = mcp.streamable_http_app()
    client = TestClient(app)

    response = client.get("/.well-known/openai-apps-domain-verification")
    assert response.status_code == 404
