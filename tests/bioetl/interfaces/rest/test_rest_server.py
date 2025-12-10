from fastapi.testclient import TestClient

from bioetl.interfaces.rest.server import create_rest_app


def test_create_rest_app_and_route_exists():
    app = create_rest_app()
    TestClient(app)
    assert any(
        r.path == "/pipelines/run" and "POST" in r.methods for r in app.router.routes
    )
