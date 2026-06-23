"""Architecture tests for observability event and unused-signal governance."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import date

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_PATH = ROOT / "configs" / "quality" / "observability_metric_governance.yaml"
EVIDENCE_PATH = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
POLICY_REVIEW_DATE = date(2026, 5, 15)

pytestmark = pytest.mark.architecture


def test_observability_governance_declares_event_signal_contracts() -> None:
    payload = yaml.safe_load(GOVERNANCE_PATH.read_text(encoding="utf-8"))

    event_governance = payload["event_signal_governance"]
    assert (
        event_governance["canonical_contract_module"]
        == "src/bioetl/domain/runtime_observability_publication_contract.py"
    )
    assert (
        event_governance["domain_mapping_module"]
        == "src/bioetl/domain/observability_event_mapping.py"
    )
    assert event_governance["declared_events_field"] == "declared_observability_events"
    assert event_governance["emitted_events_field"] == "emitted_observability_events"
    assert (
        event_governance["unused_declared_events_field"]
        == "unused_declared_observability_events"
    )
    assert (
        event_governance["retired_declared_events_field"]
        == "retired_declared_observability_events"
    )
    assert (
        event_governance["retired_declared_events_emitted_field"]
        == "retired_declared_observability_events_emitted"
    )
    assert (
        event_governance["emitted_without_contract_field"]
        == "emitted_observability_events_without_contract"
    )
    assert event_governance["event_emitters_field"] == "observability_event_emitters"
    assert event_governance["domain_event_emitters_field"] == "domain_event_emitters"
    assert (
        event_governance["canonical_emitters_field"]
        == "canonical_runtime_observability_emitters"
    )


def test_runtime_observability_event_inventory_is_committed_and_sorted() -> None:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    for key in (
        "declared_observability_events",
        "emitted_observability_events",
        "unused_declared_observability_events",
        "retired_declared_observability_events",
        "retired_declared_observability_events_emitted",
        "emitted_observability_events_without_contract",
        "domain_event_emitters",
        "canonical_runtime_observability_emitters",
    ):
        assert isinstance(payload[key], list), f"{key} must be a list"
        assert payload[key] == sorted(payload[key]), f"{key} must be deterministic"

    for key in ("observability_event_emitters",):
        assert isinstance(payload[key], dict), f"{key} must be a mapping"
        assert list(payload[key]) == sorted(payload[key]), (
            f"{key} keys must be deterministic"
        )
        for event_name, emitters in payload[key].items():
            assert isinstance(event_name, str) and event_name
            assert isinstance(emitters, list)
            assert emitters == sorted(emitters)


def test_retired_observability_event_declarations_are_governed_and_inactive() -> None:
    governance = yaml.safe_load(GOVERNANCE_PATH.read_text(encoding="utf-8"))
    event_governance = governance["event_signal_governance"]
    retired_entries = event_governance["retired_declared_events"]

    assert isinstance(retired_entries, list)
    retired_events: list[str] = []
    for entry in retired_entries:
        assert isinstance(entry, dict)
        event_name = str(entry["event_name"])
        owner = str(entry["owner"])
        reason = str(entry["reason"])
        review_date = str(entry["review_date"])

        assert entry["action"] == "retire"
        assert event_name
        assert owner.startswith("@")
        assert reason.strip()
        assert date.fromisoformat(review_date) >= POLICY_REVIEW_DATE
        retired_events.append(event_name)

    assert retired_events == sorted(retired_events)
    assert len(retired_events) == len(set(retired_events))

    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert evidence["retired_declared_observability_events"] == retired_events
    assert evidence["retired_declared_observability_events_emitted"] == []
    assert evidence["unused_declared_observability_events"] == []
