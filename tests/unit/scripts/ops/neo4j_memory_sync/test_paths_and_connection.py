"""Path and connection invariants for Neo4j memory sync tooling."""

from __future__ import annotations

import pytest

from tests.testing_support.neo4j_memory_sync import (  # noqa: F401
    test_derive_http_uri_from_bolt,
    test_memory_mapping_path_prefers_canonical_graph_mapping,
    test_resolve_neo4j_connection_does_not_leak_default_mcp_credentials_into_audit_mode,
    test_resolve_neo4j_connection_prefers_host_docker_internal_for_wsl_audit_mode,
    test_resolve_neo4j_connection_uses_audit_instance_when_live_audit_mode_enabled,
)

pytestmark = [pytest.mark.memory, pytest.mark.timeout(180)]
