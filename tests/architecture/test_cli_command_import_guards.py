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
"""Import guardrails for retained CLI compatibility seams."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.compat_shim_guards import ImportRecord

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
CLI_ROOT = SRC_ROOT / "interfaces" / "cli"
PUBLIC_COMMAND_MODULES = {
    "adr",
    "archive",
    "checkpoint",
    "cleanup",
    "config",
    "config_dq",
    "diagnostics",
    "debug",
    "export",
    "health",
    "lineage",
    "lock",
    "maintenance",
    "plan",
    "quarantine",
    "run",
    "run_all",
    "run_composite",
    "run_manifest",
    "vacuum",
    "workflow",
}


def _imported_modules_by_path(
    import_records: tuple[ImportRecord, ...],
) -> dict[Path, frozenset[str]]:
    modules_by_path: dict[Path, set[str]] = {}
    for record in import_records:
        if record.imported_name is not None and record.level != 0:
            continue
        modules_by_path.setdefault(record.path, set()).add(record.module)
    return {
        path: frozenset(module_names) for path, module_names in modules_by_path.items()
    }


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


@pytest.mark.architecture
def test_non_cli_source_avoids_interfaces_package_root_convenience_imports(
    source_import_records: tuple[ImportRecord, ...],
) -> None:
    """First-party source should import concrete interfaces directly."""
    violations: list[str] = []
    for path, imported_modules in sorted(
        _imported_modules_by_path(source_import_records).items()
    ):
        if path.is_relative_to(CLI_ROOT):
            continue
        if "bioetl.interfaces" in imported_modules:
            violations.append(_relative(path))

    assert not violations, (
        "Non-CLI source must not import the bioetl.interfaces package root. "
        "Import bioetl.interfaces.cli or bioetl.interfaces.http directly:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_non_cli_source_keeps_retained_public_cli_seams_outside_runtime_code(
    source_import_records: tuple[ImportRecord, ...],
) -> None:
    """Retained public CLI command seams are for CLI wiring and tests only."""
    violations: list[str] = []
    allowed_prefix = "bioetl.interfaces.cli.commands."

    for path, imported_modules in sorted(
        _imported_modules_by_path(source_import_records).items()
    ):
        if path.is_relative_to(CLI_ROOT):
            continue
        for module_name in imported_modules:
            if not module_name.startswith(allowed_prefix):
                continue
            suffix = module_name.removeprefix(allowed_prefix)
            if suffix.startswith("domains."):
                violations.append(f"{_relative(path)} -> {module_name}")
                continue
            if suffix in PUBLIC_COMMAND_MODULES:
                violations.append(f"{_relative(path)} -> {module_name}")

    assert not violations, (
        "Non-CLI source must not depend on retained public CLI command seams or "
        "their internal domain owners:\n" + "\n".join(violations)
    )
