"""Connection resolution must never supply a built-in audit password."""

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "configured",
    [
        {},
        {"NEO4J_PASSWORD": "main-test-value", "NEO4J_AUTH": "neo4j/main-test-value"},
        {"NEO4J_AUDIT_AUTH": "neo4j/"},
    ],
)
def test_audit_connection_requires_audit_credentials(
    monkeypatch: pytest.MonkeyPatch, configured: dict[str, str]
) -> None:
    env = {"LIVE_AUDIT_MODE": "true", **configured}
    monkeypatch.setattr(_core, "load_repo_env", lambda _root: env)

    with pytest.raises(RuntimeError, match="NEO4J_AUDIT_PASSWORD or NEO4J_AUDIT_AUTH"):
        _core.resolve_neo4j_connection(Path("unused-root"), None)


@pytest.mark.parametrize(
    ("configured", "username", "password"),
    [
        ({"NEO4J_AUDIT_PASSWORD": "audit-test-value"}, "neo4j", "audit-test-value"),
        (
            {"NEO4J_AUDIT_AUTH": "audit-user/auth-test-value"},
            "audit-user",
            "auth-test-value",
        ),
        (
            {
                "NEO4J_AUDIT_USERNAME": "explicit-user",
                "NEO4J_AUDIT_PASSWORD": "explicit-test-value",
                "NEO4J_AUDIT_AUTH": "auth-user/auth-test-value",
            },
            "explicit-user",
            "explicit-test-value",
        ),
    ],
)
def test_audit_connection_uses_configured_credentials(
    monkeypatch: pytest.MonkeyPatch,
    configured: dict[str, str],
    username: str,
    password: str,
) -> None:
    env = {"LIVE_AUDIT_MODE": "true", **configured}
    monkeypatch.setattr(_core, "load_repo_env", lambda _root: env)

    assert _core.resolve_neo4j_connection(Path("unused-root"), None) == (
        "http://localhost:7475",
        username,
        password,
        "neo4j",
    )


def test_main_connection_still_uses_main_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = {"NEO4J_AUTH": "main-user/main-test-value"}
    monkeypatch.setattr(_core, "load_repo_env", lambda _root: env)

    assert _core.resolve_neo4j_connection(Path("unused-root"), None) == (
        "http://localhost:7474",
        "main-user",
        "main-test-value",
        "neo4j",
    )
