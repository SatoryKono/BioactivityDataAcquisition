"""Full Map port bindings must not hide impls behind wrappers (#11787).

MetricsPort binds the PrometheusMetrics impl; MetricsCollector is labeled as
a compat wrapper. Declared-but-unbound ports must be covered by keep-orphan.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PARENT_MAP = (
    ROOT
    / "docs"
    / "02-architecture"
    / "diagrams"
    / "architecture"
    / "13-port-protocol-contracts.mmd"
)
FULL_VIEW = (
    ROOT
    / "docs"
    / "02-architecture"
    / "diagrams"
    / "views"
    / "13-port-protocol-contracts-full.mermaid"
)
MAPS = {"parent": PARENT_MAP, "full_view": FULL_VIEW}
ORPHAN_IDS = ("FDSP", "HCP", "MCP", "DNP", "DQMP", "SHP")

pytestmark = pytest.mark.architecture


@pytest.mark.parametrize("diagram", MAPS.values(), ids=MAPS.keys())
def test_full_map_metrics_binds_impl_not_wrapper(diagram: Path) -> None:
    source = diagram.read_text(encoding="utf-8")
    assert re.search(r"^\s*MTP --- PME\b", source, flags=re.MULTILINE)
    assert re.search(
        r'^\s*MCO\["MetricsCollector<br/>compat wrapper"\]',
        source,
        flags=re.MULTILINE,
    )


@pytest.mark.parametrize("orphan_id", ORPHAN_IDS)
@pytest.mark.parametrize("diagram", MAPS.values(), ids=MAPS.keys())
def test_full_map_binds_former_orphan_ports(diagram: Path, orphan_id: str) -> None:
    source = diagram.read_text(encoding="utf-8")
    bound = re.search(
        rf"^\s*\w+ (?:---|-->) {orphan_id}\b|^\s*{orphan_id} (?:---|-->)",
        source,
        flags=re.MULTILINE,
    )
    assert bound is not None, f"{orphan_id} has no binding edge in {diagram.name}"
    declared = re.search(
        rf"^%% keep-orphan:.*\b{orphan_id}\b", source, flags=re.MULTILINE
    )
    assert declared is None, f"{orphan_id} is bound but still listed as keep-orphan"
