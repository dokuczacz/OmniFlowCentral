import pytest


class FakeReq:
    def __init__(self, params=None, json_body=None):
        self._params = params or {}
        self._json = json_body

    @property
    def params(self):
        return self._params

    def get_json(self):
        if self._json is None:
            raise ValueError("No JSON")
        return self._json


@pytest.fixture
def fake_req():
    def _make(params=None, json_body=None):
        return FakeReq(params=params, json_body=json_body)

    return _make


@pytest.fixture(autouse=True)
def _default_env(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
    monkeypatch.setenv("AZURE_BLOB_CONTAINER_NAME", "test-container")
