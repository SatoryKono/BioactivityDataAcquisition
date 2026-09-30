"""Full Map port bindings must not hide impls behind wrappers (#11787).

MetricsPort binds the PrometheusMetrics impl; MetricsCollector is labeled as
a compat wrapper. Declared-but-unbound ports must be covered by keep-orphan.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FULL_MAP = (
    ROOT
    / "docs"
    / "02-architecture"
    / "diagrams"
    / "architecture"
    / "13-port-protocol-contracts.mmd"
)
ORPHAN_IDS = ("FDSP", "HCP", "MCP", "DNP", "DQMP", "SHP")

pytestmark = pytest.mark.architecture


def test_full_map_metrics_binds_impl_not_wrapper() -> None:
    source = FULL_MAP.read_text(encoding="utf-8")
    assert re.search(r"^\s*MTP --- PME\b", source, flags=re.MULTILINE)
    assert re.search(
        r'^\s*MCO\["MetricsCollector<br/>compat wrapper"\]',
        source,
        flags=re.MULTILINE,
    )


def test_full_map_orphans_are_declared_keep_orphan() -> None:
    source = FULL_MAP.read_text(encoding="utf-8")
    match = re.search(r"^%% keep-orphan: (.*)$", source, flags=re.MULTILINE)
    assert match is not None
    declared = {token.strip() for token in match.group(1).split(",")}
    assert set(ORPHAN_IDS) <= declared
