"""Guardrails for retired Silver filter compatibility modes."""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_LEGACY_MODE_TOKENS = (
    "legacy_semantic_silver",
    "legacy_semantic_silver_filter",
    "promoted_legacy_semantic_silver_filter",
    "BIOETL_LEGACY_SILVER_SEMANTIC",
)
FORBIDDEN_DUPLICATE_IDENTITY_TOKENS = (
    "source_profile_version",
    "silver_filter_mode",
    "silver_filter_runtime_mode",
    "silver_filter_semantic_mode",
    "silver_filter_execution_mode",
)
GUARDED_RUNTIME_CONFIG_ROOTS = (
    ROOT / "src" / "bioetl",
    ROOT / "configs",
    ROOT / ".github" / "workflows",
    ROOT / "scripts" / "engineering",
    ROOT / "scripts" / "schema",
)
GUARDED_SUFFIXES = frozenset({".py", ".yaml", ".yml", ".json", ".toml"})
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
ACTIVE_SURFACES = (
    ROOT / "src" / "bioetl" / "domain" / "config" / "runtime.py",
    ROOT / "src" / "bioetl" / "domain" / "normalization" / "_control_plane_identity.py",
    ROOT / "src" / "bioetl" / "domain" / "types" / "checkpoint_metadata.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "core"
    / "lifecycle"
    / "checkpoint_runtime.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "control_plane"
    / "manifest"
    / "_service_support.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "control_plane"
    / "manifest"
    / "identity_graph_assembly.py",
    ROOT
    / "src"
    / "bioetl"
    / "composition"
    / "runtime_builders"
    / "run_manifest_contract_identity.py",
    ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "config"
    / "silver_filter_migration.py",
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "filter_config_loader.py",
    ROOT / "docs" / "filters" / "ADR-048-silver-filters-structural-scope.md",
    ROOT / "docs" / "filters" / "migration-plan.md",
    ROOT
    / "docs"
    / "02-architecture"
    / "decisions"
    / "ADR-050-silver-structural-gold-semantic-filter-boundary.md",
)


def _iter_guarded_runtime_config_paths() -> tuple[Path, ...]:
    paths: list[Path] = []
    for root in GUARDED_RUNTIME_CONFIG_ROOTS:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix in GUARDED_SUFFIXES:
                paths.append(path)
    return tuple(paths)


@pytest.mark.architecture
def test_active_silver_filter_surfaces_do_not_expose_retired_legacy_mode() -> None:
    violations: list[str] = []
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_LEGACY_MODE_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}: {token}")

    assert not violations, (
        "Active Silver filter surfaces must not expose retired legacy mode "
        "tokens:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_silver_filter_identity_surfaces_do_not_add_deferred_or_duplicate_mode_fields() -> (
    None
):
    violations: list[str] = []
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_DUPLICATE_IDENTITY_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}: {token}")

    assert not violations, (
        "Silver filter execution identity must use only "
        "'silver_filter_compatibility_mode'; deferred or duplicate fields found:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_runtime_config_and_ci_surfaces_do_not_reintroduce_retired_silver_semantics() -> (
    None
):
    """Removed Silver semantic compatibility aliases must not return in runtime paths."""
    forbidden_tokens = (
        *FORBIDDEN_LEGACY_MODE_TOKENS,
        *FORBIDDEN_DUPLICATE_IDENTITY_TOKENS,
    )
    violations: list[str] = []

    for path in _iter_guarded_runtime_config_paths():
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}: {token}")

    assert not violations, (
        "Retired Silver semantic compatibility aliases or duplicate mode fields "
        "returned in runtime/config/CI surfaces:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_silver_filter_compatibility_guard_is_explicit_in_fail_fast_ci() -> None:
    """The Silver compatibility guard must stay in a blocking CI test slice."""
    workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")

    assert "tests/architecture/test_silver_filter_compatibility_surface.py" in workflow
    assert (
        "--deselect tests/architecture/test_silver_filter_compatibility_surface.py"
        not in workflow
    )
