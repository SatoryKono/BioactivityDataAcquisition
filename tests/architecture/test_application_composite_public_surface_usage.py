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
"""Guardrails for application.composite compatibility surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.helpers.compat_shim_guards import (
    ImportRecord,
    find_lingering_files,
    iter_compat_import_violations_from_records,
)

ROOT = Path(__file__).resolve().parents[2]
COMPAT_PARENT_IMPORTS: dict[str, frozenset[str]] = {}
ALLOWED_SRC_IMPORTS: dict[str, frozenset[Path]] = {}
ALLOWED_TEST_IMPORTS: dict[str, frozenset[Path]] = {}
REMOVED_COMPAT_MODULES = frozenset(
    {
        "bioetl.application.composite.merger_compat_mixin",
        "bioetl.application.composite.merger_compat_join_planner_mixin",
        "bioetl.application.composite.join_planner_compat_mixin",
        "bioetl.application.composite.runner",
    }
)
REMOVED_COMPAT_PARENT_IMPORTS = {
    "bioetl.application.composite": frozenset(
        {
            "merger_compat_mixin",
            "join_planner_compat_mixin",
            "runner",
        }
    )
}
REMOVED_COMPAT_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "merger_compat_mixin.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "merger_compat_join_planner_mixin.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "join_planner_compat_mixin.py",
        ROOT / "src" / "bioetl" / "application" / "composite" / "runner.py",
    }
)


def _active_compat_import_violations(
    import_records: tuple[ImportRecord, ...],
    *,
    allowed_imports: dict[str, frozenset[Path]],
) -> list[str]:
    violations: list[str] = []
    for record in import_records:
        for module_name in _record_compat_module_names(record):
            if record.path in allowed_imports[module_name]:
                continue
            rel_path = record.path.relative_to(ROOT).as_posix()
            violations.append(f"{rel_path}:{record.line_number} imports {module_name}")
    return violations


def _record_compat_module_names(record: ImportRecord) -> list[str]:
    if record.imported_name is None:
        return [record.module] if record.module in ALLOWED_SRC_IMPORTS else []
    if record.module in ALLOWED_SRC_IMPORTS:
        return [record.module]
    if record.module not in COMPAT_PARENT_IMPORTS:
        return []
    if record.imported_name not in COMPAT_PARENT_IMPORTS[record.module]:
        return []
    return [f"{record.module}.{record.imported_name}"]


@pytest.mark.architecture
def test_application_composite_compat_surfaces_are_confined_in_src(
    source_import_records: tuple[ImportRecord, ...],
) -> None:
    """First-party src must not grow new imports of active composite compat modules."""
    violations = _active_compat_import_violations(
        source_import_records,
        allowed_imports=ALLOWED_SRC_IMPORTS,
    )
    assert not violations, (
        "application.composite compatibility surfaces leaked beyond allowed src files:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_application_composite_compat_surfaces_are_confined_in_tests(
    test_import_records: tuple[ImportRecord, ...],
) -> None:
    """Ordinary tests must not accumulate new imports of active composite compat modules."""
    violations = _active_compat_import_violations(
        test_import_records,
        allowed_imports=ALLOWED_TEST_IMPORTS,
    )
    assert not violations, (
        "application.composite compatibility surfaces gained new non-smoke test imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_removed_application_composite_compat_shim_files_stay_absent() -> None:
    """Removed application.composite compat shims should stay absent."""
    lingering = find_lingering_files(root=ROOT, removed_files=REMOVED_COMPAT_FILES)
    assert not lingering, (
        "Removed application.composite compat shims must stay absent:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_removed_application_composite_compat_shims_are_not_imported(
    source_import_records: tuple[ImportRecord, ...],
    test_import_records: tuple[ImportRecord, ...],
) -> None:
    """Removed application.composite compat shims must not be imported."""
    violations = [
        *iter_compat_import_violations_from_records(
            import_records=source_import_records,
            root=ROOT,
            compat_modules=REMOVED_COMPAT_MODULES,
            compat_parent_imports=REMOVED_COMPAT_PARENT_IMPORTS,
        ),
        *iter_compat_import_violations_from_records(
            import_records=test_import_records,
            root=ROOT,
            compat_modules=REMOVED_COMPAT_MODULES,
            compat_parent_imports=REMOVED_COMPAT_PARENT_IMPORTS,
        ),
    ]
    assert not violations, (
        "Removed application.composite compat shims must stay absent from imports:\n"
        + "\n".join(violations)
    )
