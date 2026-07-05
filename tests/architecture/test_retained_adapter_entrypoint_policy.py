"""Guardrails for sanctioned public adapter entrypoint policy."""

from __future__ import annotations

import shutil
import subprocess
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


def _iter_python_file_mentions_fallback(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
    module_paths: frozenset[str],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        with py_file.open(encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                for module_path in module_paths:
                    if module_path in line:
                        violations.append(f"{rel_path}:{lineno} mentions {module_path}")
    return violations


def _iter_module_mentions(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
    module_paths: frozenset[str],
) -> list[str]:
    rg_executable = shutil.which("rg")
    if rg_executable is None:
        return _iter_python_file_mentions_fallback(
            search_root,
            allowed_files=allowed_files,
            module_paths=module_paths,
        )

    violations: list[str] = []
    allowed_paths = {path.resolve() for path in allowed_files}
    for module_path in sorted(module_paths):
        result = subprocess.run(
            [
                rg_executable,
                "-n",
                "-F",
                "--glob",
                "*.py",
                module_path,
                str(search_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode not in {0, 1}:
            raise RuntimeError(
                f"rg scan failed for {module_path!r}: {result.stderr or result.stdout}"
            )
        for row in result.stdout.splitlines():
            path_str, lineno, _line = row.split(":", 2)
            py_file = Path(path_str).resolve()
            if py_file in allowed_paths or "__pycache__" in py_file.parts:
                continue
            rel_path = py_file.relative_to(ROOT).as_posix()
            violations.append(f"{rel_path}:{lineno} mentions {module_path}")
    return violations


def _iter_legacy_path_mentions(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    return _iter_module_mentions(
        search_root,
        allowed_files=allowed_files,
        module_paths=LEGACY_IMPLEMENTATION_PATHS,
    )


def _iter_public_entrypoint_mentions(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    return _iter_module_mentions(
        search_root,
        allowed_files=allowed_files,
        module_paths=RETAINED_ENTRYPOINT_MODULES,
    )


def _iter_removed_client_shim_mentions(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    return _iter_module_mentions(
        search_root,
        allowed_files=allowed_files,
        module_paths=REMOVED_CLIENT_SHIM_MODULES,
    )


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
