"""Architecture guard for the domain composite config public seam."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architecture._platform_skip_support import mounted_worktree_skip_reason

pytestmark = [pytest.mark.timeout(180)]
if (skip_reason := mounted_worktree_skip_reason()) is not None:
    pytestmark.append(pytest.mark.skip(reason=skip_reason))

ROOT = Path(__file__).resolve().parents[2]
TARGET_MODULE = "bioetl.domain.composite.config"
SPLIT_INTERNAL_PREFIX = "bioetl.domain.composite.config_"
BASELINE_PUBLIC_SRC_IMPORTERS = 80
BASELINE_PUBLIC_TEST_IMPORTERS = 38
BASELINE_SPLIT_SRC_IMPORTERS = 7
BASELINE_SPLIT_TEST_IMPORTERS = 3
ALLOWED_EXTERNAL_SPLIT_IMPORTERS = {
    "src/bioetl/infrastructure/schemas/pipeline_config.py",
}
OWNER_SPLIT_PREFIXES = (
    "src/bioetl/domain/composite/",
    "tests/unit/domain/composite/",
)


def _module_hits(path: Path) -> tuple[bool, bool]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    public_hit = False
    split_hit = False
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
        for module_name in modules:
            if module_name == TARGET_MODULE or module_name.startswith(
                f"{TARGET_MODULE}."
            ):
                public_hit = True
            if module_name.startswith(SPLIT_INTERNAL_PREFIX):
                split_hit = True
    return public_hit, split_hit


def _collect_importers(root: Path) -> dict[str, set[str]]:
    result = {
        "public_src": set(),
        "public_tests": set(),
        "split_src": set(),
        "split_tests": set(),
    }
    for lane in ("src", "tests"):
        for path in sorted((root / lane).rglob("*.py")):
            public_hit, split_hit = _module_hits(path)
            rel_path = path.relative_to(root).as_posix()
            if public_hit:
                result[f"public_{lane}"].add(rel_path)
            if split_hit:
                result[f"split_{lane}"].add(rel_path)
    return result


@pytest.mark.architecture
def test_domain_composite_config_importer_baseline_does_not_grow() -> None:
    """The sanctioned public facade and split-internal burden must not grow."""
    importers = _collect_importers(ROOT)

    assert len(importers["public_src"]) <= BASELINE_PUBLIC_SRC_IMPORTERS
    assert len(importers["public_tests"]) <= BASELINE_PUBLIC_TEST_IMPORTERS
    assert len(importers["split_src"]) <= BASELINE_SPLIT_SRC_IMPORTERS
    assert len(importers["split_tests"]) <= BASELINE_SPLIT_TEST_IMPORTERS


@pytest.mark.architecture
def test_split_internal_importers_stay_in_owner_or_reviewed_residuals() -> None:
    """Split composite config modules must not leak to new source owners."""
    importers = _collect_importers(ROOT)
    unexpected = sorted(
        path
        for path in importers["split_src"] | importers["split_tests"]
        if not path.startswith(OWNER_SPLIT_PREFIXES)
        and path not in ALLOWED_EXTERNAL_SPLIT_IMPORTERS
    )

    assert unexpected == []
