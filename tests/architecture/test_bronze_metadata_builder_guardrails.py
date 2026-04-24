"""Architecture guardrails for legacy Bronze metadata builder imports."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TARGET_MODULE = "bioetl.infrastructure.storage.bronze.metadata_builders"
ALLOWED_IMPORTERS = {
    "src/bioetl/infrastructure/storage/bronze/metadata_mixin.py",
}


@pytest.mark.architecture
def test_runtime_code_does_not_import_legacy_bronze_metadata_builders_directly() -> None:
    violations: list[str] = []
    for path in SRC_ROOT.rglob("*.py"):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in ALLOWED_IMPORTERS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.ImportFrom) and node.module == TARGET_MODULE
            for node in ast.walk(tree)
        ):
            violations.append(relative_path)

    assert not violations, (
        "Legacy Bronze metadata builders must stay behind the canonical "
        "metadata_mixin adapter / MetadataCoordinator path. Violations:\n"
        + "\n".join(sorted(violations))
    )
