"""Architecture checks for the ADR-041 layer-aware naming policy."""

from __future__ import annotations

import ast
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

    function_rule_ids = {rule.rule_id for rule in policy.function_suffix_rules}
    assert {"composition_bootstrap_port_factories"} <= function_rule_ids

    suffix_rule_ids = {rule.rule_id for rule in policy.suffix_boundary_rules}
    assert {
        "non_domain_port_protocols",
        "non_infrastructure_adapter_aliases",
        "composition_infrastructure_service_suffix",
        "domain_service_suffix_conflict",
    } <= suffix_rule_ids

    family_rule_ids = {rule.rule_id for rule in policy.family_freeze_rules}
    assert {
        "runtime_admin_checkpoint_quarantine_family",
        "column_ordering_family",
        "composite_canonical_alias_family",
    } <= family_rule_ids

    suffix_rules = {rule.rule_id: rule for rule in policy.suffix_boundary_rules}
    allowed_service_symbols = {
        (item.symbol, item.path)
        for item in suffix_rules[
            "composition_infrastructure_service_suffix"
        ].allowed_symbols
    }
    assert allowed_service_symbols == {
        (
            "FallbackFetchOrchestratorService",
            "src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py",
        )
    }, (
        "composition/infrastructure *Service debt must stay frozen to the reviewed compat alias"
    )


def test_layer_aware_suffix_gate_detects_alias_assignments() -> None:
    """Alias assignments and public re-exports must be inspected."""
    module = _load_gate_module()
    tree = ast.parse(
        "FooPort = BarProtocol\n"
        "StorageAdapter = StorageBundle\n"
        "from somewhere import CompositePipelineRunnerService\n"
        '__all__ = ["CompositePipelineRunnerService"]\n'
        "class VisibleService: ...\n"
        "_PrivateAlias = VisibleService\n"
    )

    symbols = module._iter_layer_aware_symbols(tree)

    assert ("FooPort", 1, "alias") in symbols
    assert ("StorageAdapter", 2, "alias") in symbols
    assert ("CompositePipelineRunnerService", 3, "re-export") in symbols
    assert ("VisibleService", 5, "class") in symbols
    assert all(symbol[0] != "_PrivateAlias" for symbol in symbols)


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


def test_composition_bootstrap_port_function_exceptions_are_explicit_and_bounded() -> (
    None
):
    """Reviewed composition bootstrap `*_port` functions must stay exact."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    function_rules = {rule.rule_id: rule for rule in policy.function_suffix_rules}
    rule = function_rules["composition_bootstrap_port_factories"]

    allowed = {(item.symbol, item.path) for item in rule.allowed_symbols}
    assert allowed == {
        (
            "bootstrap_checkpoint_port",
            "src/bioetl/composition/bootstrap/assembly/checkpoint.py",
        ),
        (
            "bootstrap_composite_checkpoint_port",
            "src/bioetl/composition/bootstrap/assembly/checkpoint.py",
        ),
        (
            "bootstrap_quarantine_port",
            "src/bioetl/composition/bootstrap/assembly/checkpoint.py",
        ),
        (
            "bootstrap_dq_monitor_port",
            "src/bioetl/composition/bootstrap/runtime/dq_bootstrap.py",
        ),
        (
            "bootstrap_dq_monitor_port",
            "src/bioetl/composition/bootstrap/runtime/observability.py",
        ),
        (
            "bootstrap_logger_port",
            "src/bioetl/composition/bootstrap/runtime/logger_bootstrap.py",
        ),
        (
            "bootstrap_logger_port",
            "src/bioetl/composition/bootstrap/runtime/observability.py",
        ),
        (
            "bootstrap_metrics_port",
            "src/bioetl/composition/bootstrap/runtime/metrics_bootstrap.py",
        ),
        (
            "bootstrap_metrics_port",
            "src/bioetl/composition/bootstrap/runtime/observability.py",
        ),
        (
            "bootstrap_tracer_port",
            "src/bioetl/composition/bootstrap/runtime/tracing_bootstrap.py",
        ),
        (
            "bootstrap_tracer_port",
            "src/bioetl/composition/bootstrap/runtime/observability.py",
        ),
    }


def test_checkpoint_quarantine_manager_aliases_are_not_exported() -> None:
    """Runtime/admin modules must not retain manager-style compatibility aliases."""
    forbidden_aliases = {
        "CheckpointManager",
        "CheckpointManagerService",
        "QuarantineManager",
        "QuarantineManagerService",
    }
    module_paths = (
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "core"
        / "lifecycle"
        / "checkpoint_manager.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "quarantine_manager.py",
        ROOT / "src" / "bioetl" / "application" / "services" / "admin_runtime_api.py",
    )
    violations: list[str] = []

    for module_path in module_paths:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in forbidden_aliases:
                        violations.append(
                            f"{module_path.relative_to(ROOT)}:{node.lineno}"
                        )
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in forbidden_aliases:
                        violations.append(
                            f"{module_path.relative_to(ROOT)}:{node.lineno}"
                        )

    assert violations == [], (
        "Manager-style checkpoint/quarantine aliases must stay removed:\n"
        + "\n".join(violations)
    )


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


def test_composite_alias_family_is_frozen_to_owner_modules_only() -> None:
    """Composite canonical/compat alias family must stay confined and explicit."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    family_rules = {rule.rule_id: rule for rule in policy.family_freeze_rules}
    rule = family_rules["composite_canonical_alias_family"]

    allowed = {(item.symbol, item.path) for item in rule.allowed_symbols}
    assert allowed == {
        (
            "CompositeCheckpointService",
            "src/bioetl/application/composite/checkpoint/service.py",
        ),
        (
            "CompositeCheckpointManager",
            "src/bioetl/application/composite/checkpoint/service.py",
        ),
        (
            "CompositePipelineRunner",
            "src/bioetl/application/composite/runner_pkg/runner.py",
        ),
        (
            "CompositePipelineRunnerService",
            "src/bioetl/application/composite/runner_pkg/runner.py",
        ),
        (
            "CompositePipelineRunnerService_legacy",
            "src/bioetl/application/composite/runner_pkg/runner.py",
        ),
        (
            "CompositePreflightValidationService",
            "src/bioetl/application/composite/preflight_validator.py",
        ),
        (
            "CompositePreflightValidator",
            "src/bioetl/application/composite/preflight_validator.py",
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
