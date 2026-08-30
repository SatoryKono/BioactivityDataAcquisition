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
"""Fail-fast guard for ADR registry and governance mirror synchronization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_adr_registry import ADRRegistryGenerator


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
DECISIONS_INDEX = ROOT / "docs/02-architecture/decisions/README.md"
NAVIGATOR_REGISTRY = ROOT / "docs/02-architecture/adr-registry.md"
REGISTRY_INDEX = ROOT / "docs/02-architecture/adr-registry/index.md"
REGISTRY_JSON = ROOT / "docs/02-architecture/adr-registry/registry.json"
RULES_PATH = ROOT / "docs/00-project/RULES.md"
FILTERS_README = ROOT / "docs/filters/README.md"


def test_adr_registry_mirrors_track_latest_decision_index() -> None:
    generator = ADRRegistryGenerator()
    expected_total = len(generator.adr_index_metadata)
    latest_adr = max(generator.adr_index_metadata, key=int)

    registry_payload = json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
    registry_numbers = {
        str(entry["adr_number"]).zfill(3) for entry in registry_payload["adrs"]
    }

    assert expected_total == 60
    assert latest_adr == "060"
    assert registry_payload["total_adrs"] == expected_total
    assert len(registry_payload["adrs"]) == expected_total
    assert latest_adr in registry_numbers

    for path in (NAVIGATOR_REGISTRY, REGISTRY_INDEX):
        text = path.read_text(encoding="utf-8")
        assert f"**Total ADRs**: {expected_total}" in text
        assert f"ADR-{latest_adr}" in text
        assert "generated governance mirror" in text


def test_rules_and_requirements_do_not_publish_stale_adr_ceiling() -> None:
    rules_text = RULES_PATH.read_text(encoding="utf-8")
    decisions_index_text = DECISIONS_INDEX.read_text(encoding="utf-8")

    assert "[ADR-049]" in rules_text
    assert "[ADR-050]" in rules_text
    assert "[ADR-051]" in rules_text
    assert "[ADR-052]" in rules_text
    assert "[ADR-053]" in rules_text
    assert "[ADR-054]" in rules_text
    assert "[ADR-055]" in rules_text
    assert "[ADR-056]" in rules_text
    assert "[ADR-057]" in rules_text
    assert "[ADR-058]" in rules_text
    assert "[ADR-059]" in rules_text
    assert "ADR-050" in decisions_index_text
    assert "ADR-051" in decisions_index_text
    assert "ADR-052" in decisions_index_text
    assert "ADR-053" in decisions_index_text
    assert "ADR-054" in decisions_index_text
    assert "ADR-055" in decisions_index_text
    assert "ADR-056" in decisions_index_text
    assert "ADR-057" in decisions_index_text
    assert "ADR-058" in decisions_index_text
    assert "ADR-059" in decisions_index_text


def test_filters_docs_keep_adr_050_as_canonical_boundary() -> None:
    text = FILTERS_README.read_text(encoding="utf-8")

    assert "ADR-050" in text
    assert "accepted ADR-048 is the domain-schema/Pandera" in text
    assert "use ADR-050 for normative filter-boundary governance" in text
