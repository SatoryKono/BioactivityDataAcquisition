"""Architecture guards for canonical composite naming surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.application import composite as composite_package
from bioetl.application.composite import checkpoint as checkpoint_package
from bioetl.application.composite import preflight_validator as preflight_module
from bioetl.application.composite import runner_pkg, runtime_wiring_api
from bioetl.application.composite.runner_pkg import runner as runner_module

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TEST_ROOT = ROOT / "tests"
COMPAT_REGISTRY_PATH = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
DEPRECATED_COMPOSITE_SYMBOLS = (
    "CompositeCheckpointManager",
    "CompositePipelineRunnerService",
    "CompositePreflightValidator",
)
OWNER_ALLOWLIST = frozenset(
    {
        SRC_ROOT / "bioetl" / "application" / "composite" / "checkpoint" / "service.py",
        SRC_ROOT / "bioetl" / "application" / "composite" / "preflight_validator.py",
        SRC_ROOT / "bioetl" / "application" / "composite" / "runner_pkg" / "runner.py",
    }
)


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _symbol_hits(root: Path, allowlist: frozenset[Path]) -> list[str]:
    hits: list[str] = []
    for py_file in _python_files(root):
        if py_file in allowlist:
            continue
        source = py_file.read_text(encoding="utf-8")
        for symbol in DEPRECATED_COMPOSITE_SYMBOLS:
            if symbol in source:
                hits.append(f"{py_file.relative_to(ROOT)} -> {symbol}")
    return hits


@pytest.mark.architecture
def test_deprecated_composite_symbols_are_confined_to_owner_modules() -> None:
    hits = _symbol_hits(
        SRC_ROOT / "bioetl" / "application" / "composite", OWNER_ALLOWLIST
    )
    assert hits == [], (
        "Deprecated composite symbols must stay confined to their direct "
        "compatibility owner modules:\n" + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_first_party_composite_tests_use_canonical_names_by_default() -> None:
    roots = (
        TEST_ROOT / "unit" / "application" / "composite",
        TEST_ROOT / "unit" / "composition" / "bootstrap" / "runtime",
        TEST_ROOT / "integration" / "composite",
    )
    hits: list[str] = []
    for root in roots:
        hits.extend(_symbol_hits(root, frozenset()))
    assert hits == [], (
        "First-party composite tests must use canonical composite names by "
        "default:\n" + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_composite_facades_export_only_canonical_composite_symbols() -> None:
    composite_exports = set(composite_package.__all__)
    runtime_exports = set(runtime_wiring_api.__all__)
    checkpoint_exports = set(checkpoint_package.__all__)
    runner_exports = set(runner_pkg.__all__)
    owner_runner_exports = set(runner_module.__all__)
    owner_preflight_exports = set(preflight_module.__all__)

    assert "CompositeCheckpointService" in composite_exports
    assert "CompositePipelineRunner" in composite_exports
    assert "CompositePreflightValidationService" in composite_exports

    assert "CompositePipelineRunner" in runtime_exports
    assert "CompositePreflightValidationService" in runtime_exports
    assert "CompositeCheckpointService" in checkpoint_exports
    assert "CompositePipelineRunner" in runner_exports
    assert "CompositePipelineRunner" in owner_runner_exports
    assert "CompositePreflightValidationService" in owner_preflight_exports

    for deprecated_name in DEPRECATED_COMPOSITE_SYMBOLS:
        assert deprecated_name not in composite_exports
        assert deprecated_name not in runtime_exports
        assert deprecated_name not in checkpoint_exports
        assert deprecated_name not in runner_exports
        assert deprecated_name not in owner_runner_exports
        assert deprecated_name not in owner_preflight_exports


@pytest.mark.architecture
def test_application_composite_does_not_keep_port_types_shadow_seam() -> None:
    seam_path = SRC_ROOT / "bioetl" / "application" / "composite" / "port_types.py"
    assert not seam_path.exists(), (
        "application composite must not keep a local *Port alias seam; import "
        "domain ports directly instead."
    )

    hits = [
        str(path.relative_to(ROOT))
        for path in _python_files(SRC_ROOT / "bioetl" / "application" / "composite")
        if "from bioetl.application.composite.port_types import"
        in path.read_text(encoding="utf-8")
    ]
    assert hits == [], (
        "application composite code must not import a local port_types seam:\n"
        + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_composite_owner_module_aliases_are_curated_in_compatibility_inventory() -> (
    None
):
    """Remaining composite owner-module aliases must stay visible in the ledger."""
    payload = yaml.safe_load(COMPAT_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    rows = payload.get("transition_debt", [])
    assert isinstance(rows, list), "transition_debt must be a list"

    curated_paths = {
        row["path"]
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    assert {
        "src/bioetl/application/composite/checkpoint/service.py",
        "src/bioetl/application/composite/runner_pkg/runner.py",
        "src/bioetl/application/composite/preflight_validator.py",
    } <= curated_paths
