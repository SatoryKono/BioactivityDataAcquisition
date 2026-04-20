"""Guard test for StoragePort → narrow port migration progress.

Tracks the number of files in ``application/`` that still use the broad
``StoragePort`` aggregate instead of narrow ports (``BronzeStoragePort``,
``SilverStoragePort``, ``StorageMaintenancePort``, etc.).

Ratchet the budget down as more consumers are migrated.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_APPLICATION_ROOT = (
    Path(__file__).resolve().parents[2] / "src" / "bioetl" / "application"
)

# Maximum number of files that may still reference the broad StoragePort
# in type annotations (field declarations or function parameters).
# Ratchet this down as migrations proceed.
_MAX_BROAD_STORAGE_PORT_FILES = 0
_DI_BUNDLE_EXCEPTIONS = {
    "core/pipeline_services.py",
}


def _to_posix(path: Path) -> str:
    """Convert relative path to deterministic POSIX form."""
    return path.as_posix()


def _read_python_source(py_file: Path) -> str | None:
    try:
        return py_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _parse_python_source(source: str) -> ast.AST | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _uses_broad_storage_port_annotation(node: ast.AST) -> bool:
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.annotation, ast.Name)
        and node.annotation.id == "StoragePort"
    ):
        return True
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    return any(
        isinstance(arg.annotation, ast.Name) and arg.annotation.id == "StoragePort"
        for arg in node.args.args + node.args.kwonlyargs
    )


def _file_uses_broad_storage_port(py_file: Path) -> str | None:
    source = _read_python_source(py_file)
    if source is None or "StoragePort" not in source:
        return None

    tree = _parse_python_source(source)
    if tree is None:
        return None
    if any(_uses_broad_storage_port_annotation(node) for node in ast.walk(tree)):
        return _to_posix(py_file.relative_to(_APPLICATION_ROOT))
    return None


def _files_using_broad_storage_port() -> list[str]:
    """Return relative paths of .py files that import and annotate with StoragePort."""
    hits: list[str] = []
    for py_file in sorted(_APPLICATION_ROOT.rglob("*.py")):
        if hit := _file_uses_broad_storage_port(py_file):
            hits.append(hit)
    return hits


def _consumer_files_using_broad_storage_port() -> list[str]:
    """Return broad-port hits excluding explicit architecture allowlist."""
    return sorted(
        file_path
        for file_path in _files_using_broad_storage_port()
        if file_path not in _DI_BUNDLE_EXCEPTIONS
    )


@pytest.mark.architecture
class TestNarrowPortMigration:
    """Track progress of StoragePort → narrow port migration."""

    def test_broad_storage_port_usage_within_budget(self) -> None:
        """Files using broad StoragePort must not exceed the ratchet budget."""
        files = _consumer_files_using_broad_storage_port()
        assert len(files) <= _MAX_BROAD_STORAGE_PORT_FILES, (
            f"Found {len(files)} consumer files using broad StoragePort "
            f"(budget: {_MAX_BROAD_STORAGE_PORT_FILES}):\n"
            + "\n".join(f"  - {f}" for f in files)
        )

    def test_di_bundle_exceptions_remain_explicit(self) -> None:
        """Broad-port usage in application is allowed only for declared DI bundles."""
        files = _files_using_broad_storage_port()
        extras = sorted(
            file_path for file_path in files if file_path in _DI_BUNDLE_EXCEPTIONS
        )
        assert extras == sorted(_DI_BUNDLE_EXCEPTIONS), (
            "DI-bundle StoragePort exceptions drifted:\n"
            f"expected: {sorted(_DI_BUNDLE_EXCEPTIONS)}\n"
            f"actual:   {extras}"
        )

    def test_migrated_services_use_narrow_ports(self) -> None:
        """Verify already-migrated services no longer use broad StoragePort."""
        files = _files_using_broad_storage_port()
        migrated = [
            "services/bronze_cleanup_service.py",
            "services/medallion_maintenance_mixin.py",
            "composite/merger.py",
            "core/batch_writer.py",
            "core/lifecycle/cleanup_service.py",
            "services/medallion_lifecycle.py",
        ]
        for svc in migrated:
            assert svc not in files, f"{svc} should use a narrow port, not StoragePort"

    def test_composite_input_loader_has_no_storage_cast_fallback(self) -> None:
        """Composite read path should not rely on cast(SilverStoragePort, _storage)."""
        path = _APPLICATION_ROOT / "composite" / "merger_input_mixin.py"
        source = path.read_text(encoding="utf-8")
        assert "cast(SilverStoragePort, self._storage)" not in source
