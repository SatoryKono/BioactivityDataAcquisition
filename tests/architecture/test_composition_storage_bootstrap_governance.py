"""Architecture guardrails for composition storage naming and bootstrap context."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPOSITION_ROOT = ROOT / "src" / "bioetl" / "composition"
STORAGE_SHIM = COMPOSITION_ROOT / "factories" / "storage" / "adapter.py"
STORAGE_BUNDLE = COMPOSITION_ROOT / "factories" / "storage" / "bundle.py"
STORAGE_ASSEMBLY = COMPOSITION_ROOT / "bootstrap" / "assembly" / "storage.py"


@pytest.mark.architecture
def test_storage_bundle_is_not_defined_in_adapter_module() -> None:
    """Composition storage bundle must not use adapter naming for canonical code."""
    bundle_tree = ast.parse(STORAGE_BUNDLE.read_text(encoding="utf-8"))
    shim_tree = ast.parse(STORAGE_SHIM.read_text(encoding="utf-8"))

    assert any(
        isinstance(node, ast.ClassDef) and node.name == "StorageBundle"
        for node in bundle_tree.body
    )
    assert not any(
        isinstance(node, ast.ClassDef) and node.name == "StorageBundle"
        for node in shim_tree.body
    )


@pytest.mark.architecture
def test_composition_adapter_modules_are_limited_to_reviewed_shims() -> None:
    """New composition ``adapter.py`` modules must not reopen naming drift."""
    adapter_modules = {
        path.relative_to(ROOT).as_posix()
        for path in COMPOSITION_ROOT.rglob("adapter.py")
    }
    assert adapter_modules == {"src/bioetl/composition/factories/storage/adapter.py"}

    shim_text = STORAGE_SHIM.read_text(encoding="utf-8")
    assert "DeprecationWarning" in shim_text
    assert "2026-09-30" in shim_text
    assert "bioetl.composition.factories.storage.bundle" in shim_text


@pytest.mark.architecture
def test_shared_storage_assembly_does_not_generate_runtime_identity() -> None:
    """Shared storage assembly must receive runtime identity from the caller."""
    text = STORAGE_ASSEMBLY.read_text(encoding="utf-8")

    assert "from uuid import uuid4" not in text
    assert "uuid4(" not in text
    assert "current_utc_time" not in text
    assert "run_context: RunContext" in text
