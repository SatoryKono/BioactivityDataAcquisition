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
"""Keep ``domain/ports`` sub-modules small and focused."""

from __future__ import annotations

import pytest

import ast
from dataclasses import dataclass
from pathlib import Path

pytestmark = pytest.mark.architecture

MAX_EXPORTS_PER_PORTS_SUBMODULE = 22


@dataclass(frozen=True)
class ModuleExportStats:
    """Computed export stats for one ports sub-module."""

    module_path: Path
    export_count: int
    strategy: str


def _extract_static_all_exports(tree: ast.Module) -> list[str] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return None
        exports: list[str] = []
        for item in node.value.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                return None
            exports.append(item.value)
        return exports
    return None


def _count_declared_public_symbols(tree: ast.Module) -> int:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
    return len(names)


def _collect_module_export_stats(ports_dir: Path) -> list[ModuleExportStats]:
    stats: list[ModuleExportStats] = []
    for py_file in sorted(ports_dir.rglob("*.py")):
        rel_path = py_file.relative_to(ports_dir)
        if rel_path == Path("__init__.py"):
            # Root facade is intentionally wide; this guard is for sub-modules only.
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        static_exports = _extract_static_all_exports(tree)
        if static_exports is not None:
            stats.append(
                ModuleExportStats(
                    module_path=rel_path,
                    export_count=len(static_exports),
                    strategy="__all__",
                )
            )
            continue
        stats.append(
            ModuleExportStats(
                module_path=rel_path,
                export_count=_count_declared_public_symbols(tree),
                strategy="top_level_definitions",
            )
        )
    return stats


def test_ports_submodule_exports_stay_under_cap(src_dir: Path) -> None:
    """Every ``domain/ports`` sub-module must keep export surface small."""
    ports_dir = src_dir / "bioetl" / "domain" / "ports"
    assert ports_dir.exists(), "domain/ports directory not found"

    stats = _collect_module_export_stats(ports_dir)
    violations = [
        item for item in stats if item.export_count > MAX_EXPORTS_PER_PORTS_SUBMODULE
    ]

    assert not violations, (
        "Found oversized ports sub-modules (export surface too broad):\n"
        + "\n".join(
            "  - "
            f"{item.module_path}: {item.export_count} exports "
            f"(limit={MAX_EXPORTS_PER_PORTS_SUBMODULE}, via={item.strategy})"
            for item in violations
        )
    )
