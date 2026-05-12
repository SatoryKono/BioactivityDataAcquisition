"""Architecture checks for the ADR-041 layer-aware naming policy."""

from __future__ import annotations

import ast
from datetime import date
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
    assert {entry.layer for entry in policy.layer_suffix_matrix} == {
        "domain",
        "application",
        "infrastructure",
        "composition",
        "interfaces",
    }
    assert {entry.family_id for entry in policy.canonical_family_registry} == {
        "pipeline_execution",
        "composite_execution",
        "lock_runtime_admin",
        "storage_boundary",
    }

    function_rule_ids = {rule.rule_id for rule in policy.function_suffix_rules}
    assert {"composition_bootstrap_port_factories"} <= function_rule_ids

    suffix_rule_ids = {rule.rule_id for rule in policy.suffix_boundary_rules}
    assert {
        "non_domain_port_protocols",
        "non_infrastructure_adapter_aliases",
        "non_composition_builder_suffix",
        "composition_infrastructure_service_suffix",
        "domain_service_suffix_conflict",
    } <= suffix_rule_ids

    family_rule_ids = {rule.rule_id for rule in policy.family_freeze_rules}
    assert {
        "runtime_admin_lock_family",
        "runtime_admin_checkpoint_quarantine_family",
        "column_ordering_family",
        "composite_canonical_alias_family",
        "provider_connector_adapter_module_family",
    } <= family_rule_ids

    suffix_rules = {rule.rule_id: rule for rule in policy.suffix_boundary_rules}
    allowed_service_symbols = {
        (item.symbol, item.path)
        for item in suffix_rules[
            "composition_infrastructure_service_suffix"
        ].allowed_symbols
    }
    assert allowed_service_symbols == set(), (
        "composition/infrastructure *Service suffix boundary must stay exception-free"
    )


def test_layer_suffix_matrix_has_no_allowed_forbidden_overlap() -> None:
    """Published layer suffix matrix must stay internally coherent."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)

    for entry in policy.layer_suffix_matrix:
        assert set(entry.allowed_suffixes).isdisjoint(entry.forbidden_suffixes), (
            f"Layer suffix matrix overlap detected for {entry.layer}: "
            f"{set(entry.allowed_suffixes) & set(entry.forbidden_suffixes)}"
        )


def test_canonical_pipeline_execution_family_is_published() -> None:
    """Pipeline execution naming canon must be published machine-readably."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    registry = {item.family_id: item for item in policy.canonical_family_registry}
    family = registry["pipeline_execution"]

    canonical = {(item.symbol, item.path) for item in family.canonical_symbols}
    compatibility = {
        (item.symbol, item.path, item.reason) for item in family.compatibility_symbols
    }
    assert canonical == {
        ("PipelineRunner", "src/bioetl/application/core/runner.py"),
        (
            "PipelineService",
            "src/bioetl/application/core/pipeline_services.py",
        ),
        (
            "PipelineRunnerService",
            "src/bioetl/application/services/execution/pipeline_runner_service.py",
        ),
    }
    assert compatibility == {
        (
            "lock_manager",
            "src/bioetl/application/core/_runner_dependency_support.py",
            "Legacy dependency kwarg/property retained during staged migration.",
        ),
    }


def test_canonical_storage_boundary_family_uses_narrow_ports() -> None:
    """Storage boundary canon must stay on narrow ports, not the retired aggregate."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    registry = {item.family_id: item for item in policy.canonical_family_registry}
    family = registry["storage_boundary"]

    canonical = {(item.symbol, item.path) for item in family.canonical_symbols}
    assert canonical == {
        (
            "BronzeStoragePort",
            "src/bioetl/domain/ports/storage/bronze_port.py",
        ),
        (
            "SilverStoragePort",
            "src/bioetl/domain/ports/storage/silver_port.py",
        ),
        (
            "GoldStoragePort",
            "src/bioetl/domain/ports/storage/gold_port.py",
        ),
        (
            "MergedStoragePort",
            "src/bioetl/domain/ports/storage/merged_port.py",
        ),
    }


def test_layer_aware_suffix_gate_detects_alias_assignments() -> None:
    """Alias assignments and public re-exports must be inspected."""
    module = _load_gate_module()
    tree = ast.parse(
        "FooPort = BarProtocol\n"
        "StorageAdapter = StorageBundle\n"
        "ResultBuilder = CallableAlias\n"
        "from somewhere import CompositePipelineRunnerService\n"
        '__all__ = ["CompositePipelineRunnerService", "ResultBuilder"]\n'
        "class VisibleService: ...\n"
        "_PrivateAlias = VisibleService\n"
    )

    symbols = module._iter_layer_aware_symbols(tree)

    assert ("FooPort", 1, "alias") in symbols
    assert ("StorageAdapter", 2, "alias") in symbols
    assert ("ResultBuilder", 3, "alias") in symbols
    assert ("CompositePipelineRunnerService", 4, "re-export") in symbols
    assert ("VisibleService", 6, "class") in symbols
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


def test_lock_runtime_admin_family_is_role_driven() -> None:
    """Lock naming must encode runtime versus admin responsibility."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    family_rules = {rule.rule_id: rule for rule in policy.family_freeze_rules}
    rule = family_rules["runtime_admin_lock_family"]

    allowed = {(item.symbol, item.path) for item in rule.allowed_symbols}
    assert allowed == {
        (
            "LockRuntimeService",
            "src/bioetl/application/core/lifecycle/lock_runtime_service.py",
        ),
        (
            "LockRuntimeServiceCreateContext",
            "src/bioetl/application/core/lifecycle/lock_runtime_service.py",
        ),
        (
            "LockService",
            "src/bioetl/application/services/lock_service.py",
        ),
    }
    assert "LockCoordinator" in rule.match_regex
    assert "LockCoordinatorCreateContext" in rule.match_regex


def test_composition_bootstrap_port_function_exceptions_are_retired() -> None:
    """Composition bootstrap must not retain allowed `*_port` functions."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    function_rules = {rule.rule_id: rule for rule in policy.function_suffix_rules}
    rule = function_rules["composition_bootstrap_port_factories"]

    allowed = {(item.symbol, item.path) for item in rule.allowed_symbols}
    assert allowed == set()


def test_non_composition_builder_suffix_policy_is_exception_free() -> None:
    """Public *Builder symbols are reserved for composition-owned factories."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    suffix_rules = {rule.rule_id: rule for rule in policy.suffix_boundary_rules}
    rule = suffix_rules["non_composition_builder_suffix"]

    assert rule.suffixes == ("Builder",)
    assert rule.include_path_prefixes == ("src/bioetl/",)
    assert rule.exclude_path_prefixes == ("src/bioetl/composition/",)
    assert rule.allowed_symbols == ()
    assert {item.path for item in rule.allowed_modules} == {
        "src/bioetl/application/composite/dependency_join_context_builders.py",
        "src/bioetl/application/services/dq/dq_report_builders.py",
        "src/bioetl/application/services/lineage/metadata_lineage_node_builders.py",
        "src/bioetl/domain/value_objects/dq_report_builder.py",
        "src/bioetl/infrastructure/adapters/crossref/client_builders.py",
        "src/bioetl/infrastructure/adapters/crossref/query_builder.py",
        "src/bioetl/infrastructure/adapters/openalex/query_builder.py",
        "src/bioetl/infrastructure/adapters/pubchem/client_builders.py",
        "src/bioetl/infrastructure/adapters/pubchem/query_builder.py",
        "src/bioetl/infrastructure/adapters/uniprot/query_builder.py",
        "src/bioetl/infrastructure/storage/bronze/metadata_builders.py",
    }


def test_non_composition_builder_suffix_rejects_public_application_symbols() -> None:
    """Application-layer public *Builder symbols must fail the naming gate."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    tree = ast.parse(
        "class ResultBuilder: ...\n"
        "QueryBuilder = ResultBuilder\n"
        "from elsewhere import ExportedBuilder\n"
        '__all__ = ["ExportedBuilder"]\n'
        "class _PrivateBuilder: ...\n"
        "_PrivateAliasBuilder = ResultBuilder\n"
    )

    violations = module._layer_aware_public_symbol_violations(
        relative_path="src/bioetl/application/services/result_builders.py",
        tree=tree,
        policy=policy,
    )

    assert {
        (item.location, item.details)
        for item in violations
        if "[non_composition_builder_suffix]" in item.details
    } == {
        (
            "src/bioetl/application/services/result_builders.py:1",
            "[non_composition_builder_suffix] class ResultBuilder violates the "
            "reviewed suffix boundary for Builder",
        ),
        (
            "src/bioetl/application/services/result_builders.py:2",
            "[non_composition_builder_suffix] alias QueryBuilder violates the "
            "reviewed suffix boundary for Builder",
        ),
    }


def test_non_composition_builder_suffix_allows_composition_builder_symbols() -> None:
    """Composition owns public *Builder construction vocabulary."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    tree = ast.parse("class ResultBuilder: ...\nQueryBuilder = ResultBuilder\n")

    violations = module._layer_aware_public_symbol_violations(
        relative_path="src/bioetl/composition/runtime_builders/result_builder.py",
        tree=tree,
        policy=policy,
    )

    assert violations == []


def test_non_composition_builder_suffix_rejects_unregistered_modules() -> None:
    """Public non-composition *_builder(s).py modules must be registered."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)

    violations = module._layer_aware_module_violations(
        relative_path="src/bioetl/application/services/result_builder.py",
        policy=policy,
    )

    assert [(item.location, item.details) for item in violations] == [
        (
            "src/bioetl/application/services/result_builder.py",
            "[non_composition_builder_suffix] module result_builder.py violates "
            "the reviewed suffix boundary for Builder",
        )
    ]


def test_non_composition_builder_suffix_allows_private_modules() -> None:
    """Private helper *_builder(s).py modules remain exempt from public policy."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)

    violations = module._layer_aware_module_violations(
        relative_path="src/bioetl/application/services/_result_builder.py",
        policy=policy,
    )

    assert violations == []


def test_non_composition_builder_suffix_rejects_public_application_reexports() -> None:
    """Public application facades must not re-export *Builder names."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    tree = ast.parse(
        'from elsewhere import ResultBuilder\n__all__ = ["ResultBuilder"]\n'
    )

    violations = module._layer_aware_public_symbol_violations(
        relative_path="src/bioetl/application/services/__init__.py",
        tree=tree,
        policy=policy,
    )

    assert {
        (item.location, item.details)
        for item in violations
        if "[non_composition_builder_suffix]" in item.details
    } == {
        (
            "src/bioetl/application/services/__init__.py:1",
            "[non_composition_builder_suffix] re-export ResultBuilder violates the "
            "reviewed suffix boundary for Builder",
        )
    }


def _forbidden_alias_assignment_violation(
    module_path: Path, node: ast.Assign, forbidden_aliases: set[str]
) -> str | None:
    for target in node.targets:
        if isinstance(target, ast.Name) and target.id in forbidden_aliases:
            return f"{module_path.relative_to(ROOT)}:{node.lineno}"
    return None


def _forbidden_alias_import_violations(
    module_path: Path, node: ast.ImportFrom, forbidden_aliases: set[str]
) -> list[str]:
    return [
        f"{module_path.relative_to(ROOT)}:{node.lineno}"
        for alias in node.names
        if alias.name in forbidden_aliases
    ]


def _forbidden_alias_violations_for_module(
    module_path: Path, forbidden_aliases: set[str]
) -> list[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            violation = _forbidden_alias_assignment_violation(
                module_path, node, forbidden_aliases
            )
            if violation is not None:
                violations.append(violation)
        if isinstance(node, ast.ImportFrom):
            violations.extend(
                _forbidden_alias_import_violations(module_path, node, forbidden_aliases)
            )
    return violations


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
    violations = [
        violation
        for module_path in module_paths
        for violation in _forbidden_alias_violations_for_module(
            module_path, forbidden_aliases
        )
    ]

    assert violations == [], (
        "Manager-style checkpoint/quarantine aliases must stay removed:\n"
        + "\n".join(violations)
    )


def test_column_ordering_family_is_frozen_to_one_canonical_surface_plus_compat() -> (
    None
):
    """Column-ordering family must stay collapsed to the canonical service name."""
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
    }


def test_composite_alias_family_is_frozen_to_owner_modules_only() -> None:
    """Composite naming family must stay collapsed to the canonical surfaces."""
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
            "CompositePipelineRunner",
            "src/bioetl/application/composite/runner_pkg/runner.py",
        ),
        (
            "CompositePreflightValidationService",
            "src/bioetl/application/composite/preflight_validator.py",
        ),
    }


def test_provider_connector_adapter_family_is_owned_by_adapter_modules_only() -> None:
    """Provider adapter family must be owned by adapter.py modules only."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)
    family_rules = {rule.rule_id: rule for rule in policy.family_freeze_rules}
    rule = family_rules["provider_connector_adapter_module_family"]

    allowed = {(item.symbol, item.path) for item in rule.allowed_symbols}
    assert allowed == {
        (
            "PubMedAdapter",
            "src/bioetl/infrastructure/adapters/pubmed/adapter.py",
        ),
        (
            "SemanticScholarAdapter",
            "src/bioetl/infrastructure/adapters/semanticscholar/adapter.py",
        ),
    }

    pubmed_package = (
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "pubmed"
        / "__init__.py"
    )
    semanticscholar_package = (
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "semanticscholar"
        / "__init__.py"
    )
    assert (
        "from bioetl.infrastructure.adapters.pubmed.adapter import "
        in pubmed_package.read_text(encoding="utf-8")
    )
    assert (
        "from bioetl.infrastructure.adapters.semanticscholar.adapter import "
        in semanticscholar_package.read_text(encoding="utf-8")
    )


def test_layer_aware_suffix_policy_stays_clean_on_current_baseline() -> None:
    """Reviewed naming debt must stay fully registered with no stray violations."""
    module = _load_gate_module()
    violations = module._layer_aware_suffix_violations(ROOT)

    assert violations == [], (
        "Layer-aware naming policy drifted from the current reviewed baseline.\n"
        + "\n".join(f"{item.location}: {item.details}" for item in violations)
    )


def test_layer_aware_suffix_policy_exceptions_require_structured_expiry_metadata() -> (
    None
):
    """Naming compatibility exceptions must carry owner/expiry/removal metadata."""
    module = _load_gate_module()
    policy = module._load_layer_aware_suffix_policy(ROOT)

    allowed_symbols = []
    for rule in policy.function_suffix_rules:
        allowed_symbols.extend(rule.allowed_symbols)
    for rule in policy.suffix_boundary_rules:
        allowed_symbols.extend(rule.allowed_symbols)
    for rule in policy.family_freeze_rules:
        allowed_symbols.extend(rule.allowed_symbols)
    allowed_modules = [
        item for rule in policy.suffix_boundary_rules for item in rule.allowed_modules
    ]

    assert allowed_symbols, "Expected at least one reviewed naming exception symbol"
    today = date.today()
    for item in allowed_symbols:
        assert item.issue.startswith("#"), (
            f"Naming exception issue must be an explicit tracker reference: "
            f"{item.symbol} ({item.path})"
        )
        assert item.owner.startswith("@"), (
            f"Naming exception owner must be an explicit handle: {item.symbol} "
            f"({item.path})"
        )
        assert item.removal_step.strip(), (
            f"Naming exception removal_step must be non-empty: {item.symbol} "
            f"({item.path})"
        )
        assert date.fromisoformat(item.expires_on) >= today, (
            "Naming exception expiry is stale and must be refreshed or removed: "
            f"{item.symbol} ({item.path}) expires_on={item.expires_on}"
        )
    for item in allowed_modules:
        assert item.issue.startswith("#"), (
            f"Naming module exception issue must be an explicit tracker reference: "
            f"{item.path}"
        )
        assert item.owner.startswith("@"), (
            f"Naming module exception owner must be an explicit handle: {item.path}"
        )
        assert item.removal_step.strip(), (
            f"Naming module exception removal_step must be non-empty: {item.path}"
        )
        assert date.fromisoformat(item.expires_on) >= today, (
            "Naming module exception expiry is stale and must be refreshed or "
            f"removed: {item.path} expires_on={item.expires_on}"
        )
