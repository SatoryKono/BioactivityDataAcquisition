"""Guardrails for sanctioned public adapter entrypoint policy."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
CURRENT_TEST_FILE = Path(__file__).resolve()
LEGACY_IMPLEMENTATION_PATHS = frozenset(
    {
        "bioetl.infrastructure.adapters.pubmed.pubmed_client",
    }
)
REMOVED_CLIENT_SHIM_MODULES = frozenset(
    {
        "bioetl.infrastructure.adapters.pubmed.client",
        "bioetl.infrastructure.adapters.pubmed.pubmed_client",
        "bioetl.composition.factories.storage.adapter",
        "bioetl.infrastructure.adapters.semanticscholar.client",
    }
)
REMOVED_CLIENT_SHIM_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "pubmed"
        / "client.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "pubmed"
        / "pubmed_client.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "storage"
        / "adapter.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "semanticscholar"
        / "client.py",
    }
)
RETAINED_ENTRYPOINT_MODULES = frozenset(
    {
        "bioetl.infrastructure.adapters.pubmed.adapter",
        "bioetl.infrastructure.adapters.semanticscholar.adapter",
    }
)
ALLOWED_SRC_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "pubmed"
        / "adapter.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "semanticscholar"
        / "client.py",
    }
)
ALLOWED_RETAINED_ENTRYPOINT_SRC_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "pubmed"
        / "__init__.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "pubmed"
        / "adapter.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "semanticscholar"
        / "adapter.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "semanticscholar"
        / "__init__.py",
    }
)
ALLOWED_TEST_FILES = frozenset(
    {
        CURRENT_TEST_FILE,
        ROOT / "tests" / "architecture" / "test_layer_aware_suffix_policy.py",
        ROOT
        / "tests"
        / "unit"
        / "infrastructure"
        / "adapters"
        / "test_provider_entrypoints.py",
        ROOT / "tests" / "architecture" / "test_adapter_contracts.py",
    }
)


def _iter_legacy_path_mentions(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        lines = py_file.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for legacy_path in LEGACY_IMPLEMENTATION_PATHS:
                if legacy_path in line:
                    violations.append(f"{rel_path}:{lineno} mentions {legacy_path}")
    return violations


def _iter_public_entrypoint_mentions(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        lines = py_file.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for module_path in RETAINED_ENTRYPOINT_MODULES:
                if module_path in line:
                    violations.append(f"{rel_path}:{lineno} mentions {module_path}")
    return violations


def _iter_removed_client_shim_mentions(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        lines = py_file.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for module_path in REMOVED_CLIENT_SHIM_MODULES:
                if module_path in line:
                    violations.append(f"{rel_path}:{lineno} mentions {module_path}")
    return violations


@pytest.mark.architecture
def test_provider_client_path_shim_files_are_removed() -> None:
    """Retired provider client-path shims must not reappear."""
    existing_files = sorted(
        file_path.relative_to(ROOT).as_posix()
        for file_path in REMOVED_CLIENT_SHIM_FILES
        if file_path.exists()
    )
    assert existing_files == []


@pytest.mark.architecture
def test_provider_client_path_shim_imports_are_removed() -> None:
    """First-party src and ordinary tests must not import retired client shims."""
    allowed_files = ALLOWED_TEST_FILES | {CURRENT_TEST_FILE}
    violations = _iter_removed_client_shim_mentions(
        SRC_ROOT,
        allowed_files=frozenset(),
    ) + _iter_removed_client_shim_mentions(TESTS_ROOT, allowed_files=allowed_files)
    assert not violations, (
        "Retired provider client-path shims are still referenced:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_public_adapter_entrypoints_keep_legacy_paths_out_of_src() -> None:
    """First-party source must use sanctioned public entrypoints, not legacy paths."""
    violations = _iter_legacy_path_mentions(
        SRC_ROOT,
        allowed_files=ALLOWED_SRC_FILES,
    )
    assert not violations, (
        "Legacy adapter implementation paths leaked into first-party src/ imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_adapter_paths_are_confined_to_dedicated_compat_tests() -> None:
    """Ordinary tests must not accumulate new references to legacy adapter paths."""
    violations = _iter_legacy_path_mentions(
        TESTS_ROOT,
        allowed_files=ALLOWED_TEST_FILES,
    )
    assert not violations, (
        "Legacy adapter implementation paths gained new non-compat test usages:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_public_adapter_entrypoints_are_confined_to_package_roots_in_src() -> None:
    """First-party src should import provider package roots, not adapter owner modules."""
    violations = _iter_public_entrypoint_mentions(
        SRC_ROOT,
        allowed_files=ALLOWED_RETAINED_ENTRYPOINT_SRC_FILES,
    )
    assert not violations, (
        "Retained adapter owner modules leaked into first-party src/ beyond "
        "provider package roots:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_public_adapter_entrypoints_are_confined_to_dedicated_tests() -> None:
    """Ordinary tests should not use public adapter client modules directly."""
    violations = _iter_public_entrypoint_mentions(
        TESTS_ROOT,
        allowed_files=ALLOWED_TEST_FILES,
    )
    assert not violations, (
        "Retained adapter client entrypoints gained new non-compat test usages:\n"
        + "\n".join(violations)
    )
