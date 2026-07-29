# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Path and connection support tests for Neo4j memory sync tooling."""

from __future__ import annotations

import scripts.memory.sync as memory_sync_module

from .common import *  # noqa: F403


def test_memory_mapping_path_prefers_canonical_graph_mapping(tmp_path: Path) -> None:
    canonical = tmp_path / "src/memory/graph"
    canonical.mkdir(parents=True)
    (canonical / "mappings.yaml").write_text("version: '1.0.0'\n", encoding="utf-8")
    legacy = tmp_path / "configs/quality"
    legacy.mkdir(parents=True)
    (legacy / "neo4j_memory_mapping.yaml").write_text(
        "version: '0.9.0'\n", encoding="utf-8"
    )

    assert _memory_mapping_path(tmp_path) == canonical / "mappings.yaml"


def test_memory_mapping_excludes_generated_memory_artifacts() -> None:
    config = memory_sync_module._file_structure_config(
        _load_memory_mapping(_repo_root())
    )
    excluded_prefixes = set(config.get("excluded_prefixes", ()))

    assert "src/memory/derived" in excluded_prefixes
    assert "src/memory/episodic/sessions" in excluded_prefixes
    assert "src/memory/episodic/summaries" in excluded_prefixes
    assert "docs/site" in excluded_prefixes


def test_derive_http_uri_from_bolt() -> None:
    assert derive_http_uri("bolt://localhost:7687") == LOCALHOST_HTTP_URI
    assert (
        derive_http_uri("neo4j+s://graph.example.com:7687")
        == "https://graph.example.com:7474"
    )


def test_resolve_neo4j_connection_uses_audit_instance_when_live_audit_mode_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIVE_AUDIT_MODE", "1")
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_HTTP_URI", raising=False)
    monkeypatch.delenv("NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.delenv("NEO4J_AUTH", raising=False)

    http_uri, username, password, database = resolve_neo4j_connection(tmp_path, None)

    assert http_uri == LOCALHOST_AUDIT_HTTP_URI
    assert username == "neo4j"
    assert password == "audit_secure_password"
    assert database == "neo4j"


def test_resolve_neo4j_connection_prefers_host_docker_internal_for_wsl_audit_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIVE_AUDIT_MODE", "1")
    monkeypatch.setenv("WSL_INTEROP", "/run/WSL/123_interop")
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_HTTP_URI", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_URI", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_HTTP_URI", raising=False)

    http_uri, username, password, database = resolve_neo4j_connection(tmp_path, None)

    assert http_uri == HOST_DOCKER_INTERNAL_AUDIT_HTTP_URI
    assert username == "neo4j"
    assert password == "audit_secure_password"
    assert database == "neo4j"


def test_resolve_neo4j_connection_does_not_leak_default_mcp_credentials_into_audit_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIVE_AUDIT_MODE", "1")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "bioetl_secure_password")
    monkeypatch.setenv("NEO4J_AUTH", "neo4j/bioetl_secure_password")
    monkeypatch.delenv("NEO4J_AUDIT_USERNAME", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_PASSWORD", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_AUTH", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_URI", raising=False)
    monkeypatch.delenv("NEO4J_AUDIT_HTTP_URI", raising=False)
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)

    http_uri, username, password, database = resolve_neo4j_connection(tmp_path, None)

    assert http_uri == LOCALHOST_AUDIT_HTTP_URI
    assert username == "neo4j"
    assert password == "audit_secure_password"
    assert database == "neo4j"
