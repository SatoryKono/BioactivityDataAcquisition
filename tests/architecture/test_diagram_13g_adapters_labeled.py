"""13g data-source diagram must render labeled provider adapters (#11785).

Regression guard for #9730: every adapter id referenced by the port edge must
be declared with a human-readable label in the same file, so Mermaid never
renders bare ids.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIAGRAM_13G = (
    ROOT
    / "docs"
    / "02-architecture"
    / "diagrams"
    / "architecture"
    / "13g-port-contracts-data-sources.mmd"
)
ADAPTER_IDS = ("CA", "PA", "UA", "CRA", "OAA", "SSA", "PCA")

pytestmark = pytest.mark.architecture


def test_13g_provider_adapters_are_labeled() -> None:
    source = DIAGRAM_13G.read_text(encoding="utf-8")
    for adapter_id in ADAPTER_IDS:
        assert re.search(
            rf'^\s*{adapter_id}\["[^"]+"\]',
            source,
            flags=re.MULTILINE,
        ), f"{adapter_id} must be declared with a label in 13g"
