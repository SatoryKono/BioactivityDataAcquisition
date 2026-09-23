"""Ratchet for AUD-002 HTTP transport extract from the graph sync god-module (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
TRANSPORT = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "transport.py"
# Pre-slice line count on origin/main 62f704ba.
_CORE_LOC_BEFORE_HTTP_SLICE = 17740


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_http_transport_owns_neo4j_client_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    transport_text = TRANSPORT.read_text(encoding="utf-8")
    assert "class Neo4jHttpClient" not in core_text
    assert "class Neo4jHttpClient" in transport_text
    assert "import http.client" not in core_text
    assert "import http.client" in transport_text
    core_loc = _loc(CORE)
    transport_loc = _loc(TRANSPORT)
    assert core_loc < _CORE_LOC_BEFORE_HTTP_SLICE
    assert transport_loc < 500
