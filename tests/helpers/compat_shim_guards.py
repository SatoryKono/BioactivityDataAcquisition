"""Shared helpers for architecture tests guarding removed compatibility shims."""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ImportRecord:
    """Normalized import statement record shared by repo-wide guard tests."""

    path: Path
    line_number: int
    module: str
    imported_name: str | None = None
    level: int = 0


def find_lingering_files(*, root: Path, removed_files: Iterable[Path]) -> list[str]:
    """Return removed compatibility files that still exist in the repo."""
    return sorted(
        path.relative_to(root).as_posix() for path in removed_files if path.exists()
    )


def build_import_records(ast_cache: Mapping[Path, ast.Module]) -> tuple[ImportRecord, ...]:
    """Build a reusable import index from an already parsed AST cache."""
    records: list[ImportRecord] = []
    for py_file, tree in sorted(ast_cache.items()):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                records.extend(
                    ImportRecord(
                        path=py_file,
                        line_number=node.lineno,
                        module=alias.name,
                    )
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                records.extend(
                    ImportRecord(
                        path=py_file,
                        line_number=node.lineno,
                        module=node.module,
                        imported_name=alias.name,
                        level=node.level,
                    )
                    for alias in node.names
                )
    return tuple(records)


def iter_compat_import_violations(
    *,
    ast_cache: Mapping[Path, ast.Module],
    root: Path,
    compat_modules: frozenset[str],
    compat_parent_imports: Mapping[str, frozenset[str]],
    allowed_files: frozenset[Path] = frozenset(),
) -> list[str]:
    """Return import violations for removed compatibility modules."""
    return iter_compat_import_violations_from_records(
        import_records=build_import_records(ast_cache),
        root=root,
        compat_modules=compat_modules,
        compat_parent_imports=compat_parent_imports,
        allowed_files=allowed_files,
    )


def iter_compat_import_violations_from_records(
    *,
    import_records: Iterable[ImportRecord],
    root: Path,
    compat_modules: frozenset[str],
    compat_parent_imports: Mapping[str, frozenset[str]],
    allowed_files: frozenset[Path] = frozenset(),
) -> list[str]:
    """Return import violations from a shared import-record snapshot."""
    violations: list[str] = []
    for record in sorted(
        import_records,
        key=lambda item: (
            item.path.as_posix(),
            item.line_number,
            item.module,
            item.imported_name or "",
        ),
    ):
        if record.path in allowed_files:
            continue
        rel_path = record.path.relative_to(root).as_posix()
        violations.extend(
            f"{rel_path}:{record.line_number} imports {compat_path}"
            for compat_path in _iter_record_compat_paths(
                record=record,
                compat_modules=compat_modules,
                compat_parent_imports=compat_parent_imports,
            )
        )
    return violations


def _iter_record_compat_paths(
    *,
    record: ImportRecord,
    compat_modules: frozenset[str],
    compat_parent_imports: Mapping[str, frozenset[str]],
) -> list[str]:
    if record.imported_name is None:
        return [record.module] if record.module in compat_modules else []
    return _iter_import_from_compat_paths(
        record=record,
        compat_modules=compat_modules,
        compat_parent_imports=compat_parent_imports,
    )


def _iter_import_from_compat_paths(
    *,
    record: ImportRecord,
    compat_modules: frozenset[str],
    compat_parent_imports: Mapping[str, frozenset[str]],
) -> list[str]:
    if record.module in compat_modules:
        return [record.module]
    if record.module not in compat_parent_imports:
        return []
    compat_children = compat_parent_imports[record.module]
    if record.imported_name not in compat_children:
        return []
    return [f"{record.module}.{record.imported_name}"]
