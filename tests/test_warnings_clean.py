import pytest
from fastapi.testclient import TestClient

from invstruct.api.app import app


@pytest.mark.filterwarnings("error::DeprecationWarning")
def test_fastapi_lifespan_has_no_startup_deprecation_warning() -> None:
    assert not app.router.on_startup
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
