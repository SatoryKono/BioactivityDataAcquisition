"""Architecture checks for the ADR-041 layer-aware naming policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT / "scripts" / "engineering" / "qa" / "check_naming_package_consistency.py"
)


def _load_gate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "layer_aware_suffix_policy_runtime",
        SCRIPT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["layer_aware_suffix_policy_runtime"] = module
    spec.loader.exec_module(module)
    return module


def test_layer_aware_suffix_policy_yaml_exists_and_is_wired() -> None:
    """Canonical naming gate must stay wired to the machine-readable YAML policy."""
    module = _load_gate_module()
    policy_path = ROOT / module.LAYER_AWARE_SUFFIX_POLICY_PATH

    assert policy_path.exists(), (
        "Missing layer-aware naming policy: configs/quality/layered_suffix_policy.yaml"
    )
    assert module.LAYER_AWARE_SUFFIX_POLICY_PATH.as_posix() == (
        "configs/quality/layered_suffix_policy.yaml"
    )


def test_layer_aware_suffix_policy_registers_expected_rule_ids() -> None:
    """Policy must keep the reviewed ADR-041 boundary and family rule IDs."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)

    assert policy.version == 1
    assert policy.policy_scope == "adr_041_layer_aware_naming"

    suffix_rule_ids = {rule.rule_id for rule in policy.suffix_boundary_rules}
    assert {
        "non_domain_port_protocols",
        "composition_infrastructure_service_suffix",
        "domain_service_suffix_conflict",
    } <= suffix_rule_ids

    family_rule_ids = {rule.rule_id for rule in policy.family_freeze_rules}
    assert {
        "runtime_admin_checkpoint_quarantine_family",
        "column_ordering_family",
    } <= family_rule_ids

    suffix_rules = {rule.rule_id: rule for rule in policy.suffix_boundary_rules}
    assert (
        suffix_rules["composition_infrastructure_service_suffix"].allowed_symbols == ()
    ), "composition/infrastructure *Service debt was retired and must stay closed"


def test_checkpoint_quarantine_runtime_admin_family_is_role_driven() -> None:
    """Checkpoint/quarantine names must encode runtime versus admin responsibility."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    family_rules = {rule.rule_id: rule for rule in policy.family_freeze_rules}
    rule = family_rules["runtime_admin_checkpoint_quarantine_family"]

    allowed = {(item.symbol, item.path) for item in rule.allowed_symbols}
    assert allowed == {
        (
            "CheckpointRuntimeService",
            "src/bioetl/application/core/lifecycle/checkpoint_manager.py",
        ),
        (
            "QuarantineRuntimeService",
            "src/bioetl/application/core/quarantine_manager.py",
        ),
        (
            "CheckpointService",
            "src/bioetl/application/services/checkpoint_service.py",
        ),
        (
            "QuarantineService",
            "src/bioetl/application/services/quarantine_service.py",
        ),
    }


def test_column_ordering_family_is_frozen_to_one_canonical_surface_plus_compat() -> (
    None
):
    """Column-ordering family must keep one canonical name plus explicit compat shims."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    family_rules = {rule.rule_id: rule for rule in policy.family_freeze_rules}
    rule = family_rules["column_ordering_family"]

    allowed = {(item.symbol, item.path) for item in rule.allowed_symbols}
    assert allowed == {
        (
            "ColumnOrderService",
            "src/bioetl/application/composite/column_service.py",
        ),
        (
            "ColumnOrderer",
            "src/bioetl/application/composite/column_orderer.py",
        ),
        (
            "ColumnPriorityOrderer",
            "src/bioetl/application/composite/column_priority_orderer.py",
        ),
    }


def test_layer_aware_suffix_policy_stays_clean_on_current_baseline() -> None:
    """Reviewed naming debt must stay fully registered with no stray violations."""
    module = _load_gate_module()
    violations = module._layer_aware_suffix_violations(ROOT)

    assert violations == [], (
        "Layer-aware naming policy drifted from the current reviewed baseline.\n"
        + "\n".join(f"{item.location}: {item.details}" for item in violations)
    )
