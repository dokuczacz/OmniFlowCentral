import os
import pytest


@pytest.fixture(scope="session")
def base_url():
    """Return the base URL for integration tests.

    Set the environment variable `OMNIFLOWCENTRAL_BASE_URL` to run these tests
    against a running Functions host (e.g. http://localhost:7071).
    """
    return os.environ.get("OMNIFLOWCENTRAL_BASE_URL", "")


def pytest_collection_modifyitems(config, items):
    base = os.environ.get("OMNIFLOWCENTRAL_BASE_URL", "")
    if not base:
        # mark all integration tests as skipped unless base URL provided
        skip_reason = "OMNIFLOWCENTRAL_BASE_URL not set; skipping integration tests"
        for item in items:
            item.add_marker(pytest.mark.skip(reason=skip_reason))
