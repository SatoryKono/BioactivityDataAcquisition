"""Architecture guardrails for compatibility facade inventory docs."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_YAML = ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
POLICY_REVIEW_DATE = date(2026, 5, 15)
INVENTORY_DOC = (
    ROOT / "docs" / "02-architecture" / "07-compatibility-facade-inventory.md"
)
SNAPSHOT_DOC = ROOT / "docs" / "02-architecture" / "07-compatibility-facade-snapshot.md"
HISTORY_DOC = (
    ROOT
    / "docs"
    / "02-architecture"
    / "history"
    / "compatibility-facade-review-history.md"
)
SNAPSHOT_SCRIPT = (
    ROOT
    / "scripts"
    / "engineering"
    / "qa"
    / "generate_compatibility_facade_snapshot.py"
)
NAMING_AUDIT_SCRIPT = ROOT / "scripts" / "engineering" / "qa" / "naming_audit.py"
COMPOSITION_DOC = ROOT / "docs" / "02-architecture" / "05-composition-layer.md"
REGISTRY_GUIDE = ROOT / "docs" / "03-guides" / "registry-pattern.md"
INVENTORY_ROW_CELL_COUNT = 10


def _load_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(path.resolve()))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_registry_module() -> ModuleType:
    return _load_module(
        ROOT / "scripts" / "engineering" / "ci" / "_compatibility_registry.py",
        "compatibility_registry_loader_for_tests",
    )


def _load_naming_audit_module() -> ModuleType:
    return _load_module(
        NAMING_AUDIT_SCRIPT,
        "compatibility_inventory_naming_audit_loader",
    )


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _iter_inventory_cells(text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `src/bioetl/"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        assert len(cells) == INVENTORY_ROW_CELL_COUNT, (
            f"Unexpected inventory row format: {line}"
        )
        rows[cells[0].strip("`")] = {
            "path": cells[0].strip("`"),
            "compatibility_role": cells[1],
            "canonical_target": cells[2].strip("`"),
            "status": cells[3].strip("`"),
            "owner": cells[4].strip("`"),
            "introduced_in": cells[5].strip("`"),
            "review_date": cells[7].strip("`"),
            "allowed_call_sites": cells[6],
            "migration_path": cells[8],
            "exit_criteria": cells[9],
        }
    return rows


def _public_cli_module_from_wrapper(line: str) -> str | None:
    prefix = "from bioetl.interfaces.cli.commands."
    stripped = line.strip()
    if not stripped.startswith(prefix):
        return None
    if ".domains." in stripped:
        return None
    return stripped.removeprefix(prefix).split(" import ", 1)[0].strip()


def _domain_wrapper_points_to_public_cli(text: str) -> bool:
    return (
        '"""Internal wrapper for the public ' in text
        and "from bioetl.interfaces.cli.commands." in text
        and "from bioetl.interfaces.cli.commands.domains.shared." not in text
    )


def _public_cli_path_for_module(module_name: str, commands_root: Path) -> Path:
    return commands_root / f"{module_name.replace('.', '/')}.py"


def _public_cli_path_from_wrapper_line(line: str, *, commands_root: Path) -> str | None:
    module_name = _public_cli_module_from_wrapper(line)
    if module_name is None:
        return None
    public_path = _public_cli_path_for_module(module_name, commands_root)
    if not public_path.exists():
        return None
    return public_path.relative_to(ROOT).as_posix()


def _iter_public_cli_paths_for_wrapper(path: Path, *, commands_root: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    if not _domain_wrapper_points_to_public_cli(text):
        return set()

    paths: set[str] = set()
    for line in text.splitlines():
        public_path = _public_cli_path_from_wrapper_line(
            line, commands_root=commands_root
        )
        if public_path is not None:
            paths.add(public_path)
    return paths


def _iter_cli_public_entrypoint_paths() -> set[str]:
    paths: set[str] = set()
    domains_root = (
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "domains"
    )
    commands_root = ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands"
    for path in domains_root.rglob("*.py"):
        paths.update(
            _iter_public_cli_paths_for_wrapper(path, commands_root=commands_root)
        )
    return paths


@pytest.mark.architecture
def test_registry_yaml_has_expected_shape() -> None:
    """Compatibility registry YAML must be the canonical structured source."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)

    assert registry.version == 1
    assert registry.policy_scope == "compatibility_facades"
    assert registry.tracked_docstring_prefixes
    assert registry.retained_entrypoints

    for row in registry.curated_rows:
        assert row.status in mod.ALLOWED_COMPATIBILITY_STATUSES
        assert row.path.startswith("src/bioetl/")
        assert row.owner
        assert row.canonical_target
        assert row.migration_path
        assert row.exit_criteria
        assert isinstance(row.external_breaking_change_required, bool)
        assert isinstance(row.internal_callers_zero, bool)
        assert row.external_breaking_change_required is True, (
            "Retained public entrypoints must declare that removal requires an "
            f"external breaking-change process: {row.path}"
        )
        assert date.fromisoformat(row.review_date).year >= 2026
        assert date.fromisoformat(row.review_date) >= POLICY_REVIEW_DATE, (
            "Compatibility facade review metadata is stale and must be refreshed "
            f"before merge: {row.path} review_date={row.review_date}"
        )

    for row in registry.measured_only_modules:
        assert row.path.startswith("src/bioetl/")
        assert row.owner
        assert row.reason
        assert date.fromisoformat(row.review_date).year >= 2026
        assert row.new_code_policy in mod.ALLOWED_MEASURED_ONLY_NEW_CODE_POLICIES
        assert row.promotion_trigger in mod.ALLOWED_MEASURED_ONLY_PROMOTION_TRIGGERS

    assert registry.measured_only_ratchet.max_total_modules >= len(
        registry.measured_only_modules
    )
    if not registry.measured_only_modules:
        assert registry.measured_only_ratchet.max_total_modules == 0
        assert all(
            scope.max_modules == 0
            for scope in registry.measured_only_ratchet.scoped_limits
        )
    assert registry.measured_only_ratchet.scoped_limits
    assert registry.measured_only_review_workflow.required_checks
    assert registry.measured_only_review_workflow.allowed_outcomes
    assert (
        registry.measured_only_review_workflow.review_cadence
        in mod.ALLOWED_MEASURED_ONLY_REVIEW_CADENCES
    )


@pytest.mark.architecture
def test_retained_entrypoint_burn_down_plan_covers_all_public_rows() -> None:
    """Retained public entrypoints must declare an explicit burn-down plan."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)
    payload = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    burn_down_plan = payload["retained_entrypoint_burn_down_plan"]

    assert burn_down_plan["linked_issue"] == "#4565"
    assert burn_down_plan["review_date"] == "2026-09-30"
    allowed_phases = set(burn_down_plan["allowed_phases"])
    assert allowed_phases == {
        "visibility",
        "narrow-first-party-callers",
        "enforce",
    }
    allowed_target_states = set(burn_down_plan["allowed_target_states"])
    assert allowed_target_states == {
        "retain_as_stable_public_api",
        "narrow_first_party_callers",
    }

    rows = burn_down_plan["rows"]
    paths_by_review = {row["path"]: row for row in rows}
    assert set(paths_by_review) == {row.path for row in registry.retained_entrypoints}
    for path, row in paths_by_review.items():
        assert row["phase"] in allowed_phases, path
        assert row["target_state"] in allowed_target_states, path
        assert str(row["rationale"]).strip(), path
        assert str(row["completion_gate"]).strip(), path


@pytest.mark.architecture
def test_inventory_doc_exists_with_required_sections() -> None:
    """Operational compatibility doc must keep the manual sections only."""
    assert INVENTORY_DOC.exists(), (
        "Missing compatibility facade inventory doc: "
        "docs/02-architecture/07-compatibility-facade-inventory.md"
    )

    text = INVENTORY_DOC.read_text(encoding="utf-8")
    for heading in (
        "# Compatibility Facade Inventory",
        "## Status Model",
        "## Governance Freeze",
        "## Mandatory Artifact Sync",
        "## Inventory",
        "### Transition Debt Ledger",
        "### Sanctioned Public Entrypoints",
        "## Generated Snapshot",
        "## Usage Notes",
        "## Measured-Only Lifecycle Review",
        "## Measured-Only Ratchet",
        "## Historical Review Log",
    ):
        assert heading in text, f"Missing heading in inventory doc: {heading}"

    assert "## Measured Registry" not in text, (
        "Measured registry must live in the generated companion file, "
        "not in the manual operational doc."
    )
    assert "## Measured-Only Policy" in text, (
        "Operational compatibility doc must state the measured-only policy "
        "separately from the generated snapshot."
    )
    assert "not sanctioned public import targets" in text, (
        "Operational compatibility doc must explicitly state that measured-only "
        "modules are not sanctioned public import targets."
    )


@pytest.mark.architecture
def test_inventory_doc_declares_canonical_sync_commands() -> None:
    """Operational doc must point to the canonical registry and snapshot commands."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")

    required_snippets = (
        "configs/quality/compatibility_facade_inventory.yaml",
        "docs/02-architecture/07-compatibility-facade-snapshot.md",
        "./.venv/Scripts/python.exe scripts/engineering/qa/generate_compatibility_facade_snapshot.py --check",
        "./.venv/Scripts/python.exe scripts/engineering/qa/generate_compatibility_facade_snapshot.py --update",
        "./.venv/Scripts/python.exe scripts/engineering/qa/generate_architecture_dependency_map.py --check",
        "./.venv/Scripts/python.exe scripts/engineering/qa/generate_architecture_dependency_map.py --update",
        "./.venv/Scripts/python.exe -m pytest tests/architecture/test_compatibility_facade_inventory.py -q",
    )

    for snippet in required_snippets:
        assert snippet in text, (
            "Compatibility facade inventory doc must keep canonical sync guidance "
            f"for registry + generated snapshot artifacts: missing {snippet}"
        )


@pytest.mark.architecture
def test_inventory_doc_declares_dependency_map_scope_boundary() -> None:
    """Operational doc must explain what the dependency map does not measure."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")
    assert "layer-policy/topology snapshot only" in text, (
        "Compatibility facade inventory doc must describe the dependency-map "
        "artifact as a layer-policy/topology snapshot."
    )
    assert "MUST NOT be inferred from zero layer violations alone" in text, (
        "Operational sync guidance must keep hotspot/duplication pressure "
        "separate from zero dependency-map violations."
    )


@pytest.mark.architecture
def test_inventory_doc_tables_match_yaml_registry() -> None:
    """Manual curated ledger tables must match the YAML SSOT field-for-field."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)
    doc_rows = _iter_inventory_cells(INVENTORY_DOC.read_text(encoding="utf-8"))

    assert set(doc_rows) == registry.curated_paths, (
        "Curated compatibility tables drifted from YAML registry rows.\n"
        "Documented:\n"
        + "\n".join(sorted(doc_rows))
        + "\nExpected:\n"
        + "\n".join(sorted(registry.curated_paths))
    )

    for row in registry.curated_rows:
        doc_row = doc_rows[row.path]
        assert doc_row["status"] == row.status
        assert doc_row["canonical_target"] == row.canonical_target
        assert doc_row["owner"] == row.owner
        assert doc_row["introduced_in"] == row.introduced_in
        assert doc_row["review_date"] == row.review_date
        assert _normalize(doc_row["compatibility_role"]) == _normalize(
            row.compatibility_role
        )
        assert _normalize(doc_row["allowed_call_sites"]) == _normalize(
            row.allowed_call_sites
        )
        assert _normalize(doc_row["migration_path"]) == _normalize(row.migration_path)
        assert _normalize(doc_row["exit_criteria"]) == _normalize(row.exit_criteria)


@pytest.mark.architecture
def test_generated_snapshot_companion_is_present_and_in_sync() -> None:
    """Generated compatibility snapshot must stay synchronized with YAML + code scan."""
    assert SNAPSHOT_DOC.exists(), (
        "Missing generated compatibility snapshot doc: "
        "docs/02-architecture/07-compatibility-facade-snapshot.md"
    )

    result = subprocess.run(
        [sys.executable, str(SNAPSHOT_SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, (
        "Generated compatibility snapshot drifted.\n"
        + (result.stdout or "")
        + (result.stderr or "")
    )


@pytest.mark.architecture
def test_cli_public_entrypoint_modules_are_curated_rows() -> None:
    """Every retained top-level CLI public seam must be explicitly inventoried."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)

    missing = sorted(_iter_cli_public_entrypoint_paths() - registry.curated_paths)
    assert not missing, (
        "CLI public entrypoint modules are missing from the curated compatibility "
        "ledger.\n" + "\n".join(missing)
    )


@pytest.mark.architecture
def test_public_symbol_alias_surfaces_are_curated_rows() -> None:
    """Named public symbol alias surfaces must anchor to the curated ledger."""
    compat_mod = _load_registry_module()
    naming_mod = _load_naming_audit_module()
    compat_registry = compat_mod.load_compatibility_registry(REGISTRY_YAML)
    naming_registry = naming_mod.load_naming_registry()

    missing = sorted(
        surface
        for entry in naming_registry.public_symbol_aliases
        for surface in (entry.defining_surface, *entry.export_surfaces)
        if surface not in compat_registry.curated_paths
    )
    assert not missing, (
        "Public symbol alias surfaces must be covered by the curated "
        "compatibility ledger.\n" + "\n".join(missing)
    )


@pytest.mark.architecture
def test_deprecated_module_alias_surfaces_remain_in_transition_debt() -> None:
    """Retired CLI alias helpers must not linger in transition-debt review."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)

    transition_paths = {row.path for row in registry.transition_debt}
    assert "src/bioetl/interfaces/cli/commands/_compat.py" not in transition_paths, (
        "CLI compatibility alias helper should be retired from transition debt."
    )
    assert (
        "src/bioetl/composition/factories/storage/adapter.py" not in transition_paths
    ), "Retired storage adapter shim must not remain in transition debt."
    assert (
        "src/bioetl/application/composite/checkpoint/anchor_context.py"
        not in transition_paths
    ), "Retired checkpoint anchor-context shim must not remain in transition debt."


@pytest.mark.architecture
def test_retired_maintenance_domain_wrapper_modules_are_absent() -> None:
    """Retired maintenance wrappers must not return as hidden compatibility facades."""
    retired = (
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "maintenance"
    )
    retired_paths = [
        retired / "archive.py",
        retired / "cleanup.py",
        retired / "vacuum.py",
    ]

    assert not [path for path in retired_paths if path.exists()], (
        "Maintenance domain compatibility wrappers were retired; "
        "lazy loading must target the public command modules directly."
    )


@pytest.mark.architecture
def test_retired_run_domain_wrapper_module_is_absent() -> None:
    """Run command compatibility wrapper must stay retired after seam collapse."""
    retired_path = (
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "run"
        / "command.py"
    )
    assert not retired_path.exists(), (
        "Run command compatibility wrapper was retired; "
        "domain package lazy loading must target the public run module directly."
    )


@pytest.mark.architecture
def test_placeholder_orchestration_package_is_absent() -> None:
    """Placeholder orchestration package should not remain importable or shipped."""
    retired_path = ROOT / "src" / "bioetl" / "interfaces" / "orchestration"
    assert not retired_path.exists(), (
        "Reserved interfaces.orchestration placeholder package was retired and must "
        "not return to the public runtime surface."
    )


@pytest.mark.architecture
def test_cli_sys_modules_alias_helper_is_retired() -> None:
    """CLI command wrappers must not rely on runtime `sys.modules` aliasing."""
    helper_path = (
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "_compat.py"
    )
    assert not helper_path.exists()

    offenders: list[str] = []
    for path in (ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands").rglob(
        "*.py"
    ):
        text = path.read_text(encoding="utf-8")
        if "alias_module(" in text:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert not offenders, (
        "CLI command wrappers must use direct re-export seams instead of "
        "runtime module aliasing.\n" + "\n".join(sorted(offenders))
    )


@pytest.mark.architecture
def test_measured_only_allowlist_matches_docstring_scan() -> None:
    """Measured-only allowlist must match the tracked compatibility docstrings."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)
    unexpected, missing = mod.validate_measured_docstring_surface(registry)

    assert not unexpected, (
        "Unexpected docstring-tracked compatibility modules detected:\n"
        + "\n".join(sorted(unexpected))
    )
    assert not missing, (
        "Allowlisted measured-only modules no longer expose tracked "
        "compatibility docstrings:\n" + "\n".join(sorted(missing))
    )


@pytest.mark.architecture
def test_snapshot_generator_rejects_parent_traversal_relative_output() -> None:
    """Snapshot generator must reject parent traversal in relative output paths."""
    module = _load_module(
        SNAPSHOT_SCRIPT,
        "compatibility_facade_snapshot_security_loader",
    )

    with pytest.raises(ValueError, match=r"outside|canonical tracked artifact"):
        module._resolve_canonical_output_path("../escape.md")


@pytest.mark.architecture
def test_snapshot_generator_rejects_noncanonical_repo_output() -> None:
    """Snapshot generator must not write to arbitrary repo-local markdown paths."""
    module = _load_module(
        SNAPSHOT_SCRIPT,
        "compatibility_facade_snapshot_security_loader_noncanonical",
    )

    with pytest.raises(ValueError, match="canonical tracked artifact"):
        module._resolve_canonical_output_path(
            "docs/02-architecture/not-the-snapshot.md"
        )


@pytest.mark.architecture
def test_first_party_src_does_not_import_measured_only_modules() -> None:
    """Measured-only compatibility modules must stay out of first-party src imports."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)
    violations = mod.find_first_party_imports_of_measured_only_modules(registry)

    assert not violations, (
        "First-party src must not import measured-only compatibility modules.\n"
        + "\n".join(
            f"{module} <- {', '.join(importers)}"
            for module, importers in sorted(violations.items())
        )
    )


@pytest.mark.architecture
def test_internal_callers_zero_rows_have_no_first_party_src_imports() -> None:
    """Rows marked internal_callers_zero must stay out of first-party src imports."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)
    violations = mod.find_first_party_imports_of_internal_callers_zero_rows(registry)

    assert not violations, (
        "Compatibility rows marked internal_callers_zero still have first-party "
        "src importers.\n"
        + "\n".join(
            f"{module} <- {', '.join(importers)}"
            for module, importers in sorted(violations.items())
        )
    )


@pytest.mark.architecture
def test_measured_only_ratchet_budget_is_not_exceeded() -> None:
    """Measured-only compatibility surface must stay within the reviewed ratchet."""
    mod = _load_registry_module()
    registry = mod.load_compatibility_registry(REGISTRY_YAML)
    violations, scoped_counts = mod.validate_measured_only_ratchet(registry)

    assert not violations, (
        "Measured-only compatibility surface exceeded its ratchet budget.\n"
        + "\n".join(violations)
        + "\nCurrent scoped counts:\n"
        + "\n".join(
            f"{path_prefix}={count}"
            for path_prefix, count in sorted(scoped_counts.items())
        )
    )


@pytest.mark.architecture
def test_inventory_doc_declares_measured_only_lifecycle_workflow() -> None:
    """Operational doc must explain lifecycle review outcomes for measured-only seams."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")

    for snippet in (
        "review cadence is quarterly",
        "retain",
        "promote",
        "remove",
        "Promotions into the curated ledger are required",
        "Ratchet budgets are enforced",
    ):
        assert snippet in text, (
            "Compatibility facade inventory doc must keep measured-only lifecycle "
            f"workflow guidance for {snippet!r}"
        )


@pytest.mark.architecture
def test_inventory_doc_links_snapshot_and_history() -> None:
    """Operational doc must point to the generated snapshot and the history doc."""
    text = INVENTORY_DOC.read_text(encoding="utf-8")
    assert "07-compatibility-facade-snapshot.md" in text, (
        "Inventory doc must link the generated snapshot companion."
    )
    assert "history/compatibility-facade-review-history.md" in text, (
        "Inventory doc must link the extracted history doc."
    )
    assert HISTORY_DOC.exists(), "Missing compatibility facade history doc."


@pytest.mark.architecture
def test_inventory_doc_is_linked_from_discovery_docs() -> None:
    """Inventory should remain discoverable from composition and registry docs."""
    inventory_name = "07-compatibility-facade-inventory.md"
    for doc_path in (COMPOSITION_DOC, REGISTRY_GUIDE):
        text = doc_path.read_text(encoding="utf-8")
        assert inventory_name in text, (
            f"{doc_path.relative_to(ROOT)} must link to {inventory_name}"
        )


@pytest.mark.architecture
def test_src_outside_composition_avoids_internal_composition_entrypoint_modules() -> (
    None
):
    """First-party source outside composition should use public composition APIs."""
    internal_modules = frozenset(
        {
            "bioetl.composition._pipeline_execution",
            "bioetl.composition._resource_management",
        }
    )
    violations: list[str] = []

    for path in (ROOT / "src" / "bioetl").rglob("*.py"):
        rel_path = path.relative_to(ROOT)
        rel_text = rel_path.as_posix()
        if rel_text.startswith("src/bioetl/composition/"):
            continue

        text = path.read_text(encoding="utf-8")
        for module in internal_modules:
            token = f"from {module} import"
            import_token = f"import {module}"
            if token in text or import_token in text:
                violations.append(rel_text)
                break

    assert not violations, (
        "First-party src outside composition must use sanctioned public "
        "composition APIs instead of internal composition entrypoint modules:\n"
        + "\n".join(sorted(violations))
    )
