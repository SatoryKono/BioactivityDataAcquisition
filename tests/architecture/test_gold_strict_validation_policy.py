"""Architecture guards for Gold strict-validation policy separation and waivers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from bioetl.domain.config import DQConfig, RuntimeConfig
from bioetl.domain.types import RunType

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSITE_CONTRACTS_DIR = PROJECT_ROOT / "configs" / "contracts" / "composite"
COMPOSITE_WAIVERS_PATH = (
    PROJECT_ROOT / "configs" / "quality" / "composite_gold_strictness_waivers.yaml"
)
GOLD_CONTRACT_DOC_PATH = PROJECT_ROOT / "docs" / "04-reference" / "contracts" / "gold-schemas.md"


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict), f"{path} must contain a YAML mapping"
    return payload


def _load_composite_contracts() -> dict[str, dict[str, object]]:
    contracts: dict[str, dict[str, object]] = {}
    for path in sorted(COMPOSITE_CONTRACTS_DIR.glob("*.yaml")):
        payload = _load_yaml(path)
        contract_ref = payload.get("contract_ref")
        assert isinstance(contract_ref, str) and contract_ref.startswith("composite."), (
            f"{path} must declare a composite contract_ref"
        )
        contracts[contract_ref] = payload
    return contracts


@pytest.mark.architecture
def test_runtime_gold_strictness_stays_separate_from_dq_strict_defaults() -> None:
    """DQ strict defaults must not weaken the runtime Gold strictness baseline."""
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    dq_config = DQConfig()

    assert runtime.strict_gold_validation is True
    assert dq_config.strict_validation is False


@pytest.mark.architecture
def test_composite_dq_strict_false_contracts_require_explicit_waiver_metadata() -> None:
    """Composite contracts using DQ-only strict=false must declare a tracked waiver."""
    contracts = _load_composite_contracts()
    waiver_payload = _load_yaml(COMPOSITE_WAIVERS_PATH)

    waivers = waiver_payload.get("waivers")
    assert isinstance(waivers, list), "composite strictness waiver file must define a waivers list"
    waiver_map: dict[str, dict[str, object]] = {}
    for waiver in waivers:
        assert isinstance(waiver, dict), "waiver entries must be mappings"
        contract_ref = waiver.get("contract_ref")
        assert isinstance(contract_ref, str) and contract_ref, (
            "each waiver entry must define contract_ref"
        )
        waiver_map[contract_ref] = waiver

    refs_requiring_waiver = {
        contract_ref
        for contract_ref, payload in contracts.items()
        if payload.get("strict_dq_validation") is False
    }

    assert set(waiver_map) == refs_requiring_waiver

    for contract_ref in sorted(refs_requiring_waiver):
        waiver = waiver_map[contract_ref]
        owner = waiver.get("owner")
        rationale = waiver.get("rationale")
        approved_on = waiver.get("approved_on")
        expires_on = waiver.get("expires_on")
        linked_issue = waiver.get("linked_issue")
        enforcement_context = waiver.get("enforcement_context")

        assert isinstance(owner, str) and owner
        assert isinstance(rationale, str) and rationale.strip()
        assert isinstance(linked_issue, str) and linked_issue == "#4768"
        assert (
            isinstance(enforcement_context, str)
            and enforcement_context == "composite_merged_gold_write"
        )

        assert isinstance(approved_on, str) and approved_on
        assert isinstance(expires_on, str) and expires_on
        approved_date = date.fromisoformat(approved_on)
        expiry_date = date.fromisoformat(expires_on)
        assert approved_date < expiry_date
        assert (expiry_date - approved_date).days <= 365


@pytest.mark.architecture
def test_gold_contract_docs_reference_composite_strictness_waiver_policy() -> None:
    """Published Gold-contract docs must point readers to the waiver registry."""
    content = GOLD_CONTRACT_DOC_PATH.read_text(encoding="utf-8")
    assert "configs/quality/composite_gold_strictness_waivers.yaml" in content
