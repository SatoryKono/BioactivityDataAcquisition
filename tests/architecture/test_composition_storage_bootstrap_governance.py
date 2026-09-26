# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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

    assert any(
        isinstance(node, ast.ClassDef) and node.name == "StorageBundle"
        for node in bundle_tree.body
    )
    assert not STORAGE_SHIM.exists()


@pytest.mark.architecture
def test_composition_adapter_modules_are_limited_to_reviewed_shims() -> None:
    """Composition ``adapter.py`` modules must not reopen naming drift."""
    adapter_modules = {
        path.relative_to(ROOT).as_posix()
        for path in COMPOSITION_ROOT.rglob("adapter.py")
    }
    assert adapter_modules == set()


@pytest.mark.architecture
def test_shared_storage_assembly_does_not_generate_runtime_identity() -> None:
    """Shared storage assembly must receive runtime identity from the caller."""
    text = STORAGE_ASSEMBLY.read_text(encoding="utf-8")

    assert "from uuid import uuid4" not in text
    assert "uuid4(" not in text
    assert "current_utc_time" not in text
    assert "run_context: RunContext" in text
    assert "NoOpValidator" not in text
    assert "PanderaSilverValidator" in text
