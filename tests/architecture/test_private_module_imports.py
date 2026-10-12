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
"""Owner-aware guardrail for first-party private-module imports in src/.

Same-owner ``._*`` imports are allowed. Cross-owner private-module imports
are tracked in ``configs/quality/private_import_ratchet.yaml`` as a
shrink-only baseline (``STRICT_PRIVATE_IMPORT_GUARD = False``). The YAML
``max_count`` must equal the live observed pair count and must not grow.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.engineering.qa.report_private_import_inventory import (
    allowed_pairs_from_config,
    evaluate_ratchet,
    load_ratchet_config,
)

STRICT_PRIVATE_IMPORT_GUARD = False
RATCHET_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "quality"
    / "private_import_ratchet.yaml"
)


def _allowed_baseline_imports() -> frozenset[tuple[str, str]]:
    return allowed_pairs_from_config(load_ratchet_config(RATCHET_CONFIG_PATH))


ALLOWED_BASELINE_IMPORTS = _allowed_baseline_imports()


def _module_name_for_path(src_dir: Path, file_path: Path) -> str:
    rel_parts = file_path.relative_to(src_dir).with_suffix("").parts
    return ".".join(rel_parts)


def _collect_existing_modules_from_cache(
    source_ast_cache: dict[Path, ast.Module],
    *,
    src_dir: Path,
) -> frozenset[str]:
    """Build the module set from the shared architecture AST index."""
    modules: set[str] = set()
    for py_file in source_ast_cache:
        try:
            rel_path = py_file.resolve().relative_to(src_dir.resolve())
        except ValueError:
            continue
        if py_file.name == "__init__.py":
            modules.add(".".join(rel_path.parent.parts))
            continue
        modules.add(".".join(rel_path.with_suffix("").parts))
    return frozenset(modules)


def _resolve_relative_module(
    *,
    importer_module: str,
    module: str | None,
    level: int,
) -> str | None:
    if level == 0:
        return module

    parent_parts = importer_module.split(".")[:-1]
    if level > len(parent_parts):
        return None

    base_parts = parent_parts[: len(parent_parts) - level + 1]
    if module:
        return ".".join([*base_parts, module])
    return ".".join(base_parts)


def _module_exists(existing_modules: frozenset[str], module: str) -> bool:
    return module in existing_modules


def _iter_candidate_import_targets(
    *,
    existing_modules: frozenset[str],
    importer_module: str,
    node: ast.AST,
) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names if alias.name.startswith("bioetl.")]

    if not isinstance(node, ast.ImportFrom):
        return []

    base_module = _resolve_relative_module(
        importer_module=importer_module,
        module=node.module,
        level=node.level,
    )
    if not base_module or not base_module.startswith("bioetl."):
        return []

    candidates = [base_module]
    for alias in node.names:
        if alias.name == "*":
            continue
        nested_module = f"{base_module}.{alias.name}"
        if _module_exists(existing_modules, nested_module):
            candidates.append(nested_module)
    return candidates


def _is_private_module(module: str) -> bool:
    return any(part.startswith("_") for part in module.split("."))


def _collect_external_private_imports(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> dict[tuple[str, str], list[int]]:
    violations: dict[tuple[str, str], list[int]] = {}
    existing_modules = _collect_existing_modules_from_cache(
        source_ast_cache,
        src_dir=src_dir,
    )
    resolved_src = src_dir.resolve()

    for py_file, tree in sorted(
        source_ast_cache.items(),
        key=lambda item: item[0].as_posix(),
    ):
        try:
            rel_path = py_file.resolve().relative_to(resolved_src).as_posix()
        except ValueError:
            continue
        importer_module = _module_name_for_path(src_dir, py_file)
        importer_owner = importer_module.rsplit(".", 1)[0]

        for node in ast.walk(tree):
            for target_module in _iter_candidate_import_targets(
                existing_modules=existing_modules,
                importer_module=importer_module,
                node=node,
            ):
                if not _is_private_module(target_module):
                    continue
                target_owner = target_module.rsplit(".", 1)[0]
                if importer_owner == target_owner:
                    continue
                key = (rel_path, target_module)
                violations.setdefault(key, []).append(getattr(node, "lineno", 0))

    return violations


@pytest.mark.architecture
@pytest.mark.slow
def test_owner_aware_private_module_imports(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Cross-owner imports of first-party private modules are forbidden in src/."""
    violations = _collect_external_private_imports(src_dir, source_ast_cache)
    observed = frozenset(violations)

    if STRICT_PRIVATE_IMPORT_GUARD:
        assert not observed, (
            "External first-party private-module imports detected in src/:\n"
            + "\n".join(
                f"  - {path}:{min(lines)} -> {module}"
                for (path, module), lines in sorted(violations.items())
            )
        )
        return

    unexpected = observed - ALLOWED_BASELINE_IMPORTS
    assert not unexpected, (
        "New external first-party private-module imports introduced:\n"
        + "\n".join(
            f"  - {path}:{min(violations[(path, module)])} -> {module}"
            for path, module in sorted(unexpected)
        )
    )


@pytest.mark.architecture
def test_private_import_baseline_is_monotonically_non_increasing(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """#9597: YAML max_count is shrink-only and must match live observed pairs."""
    config = load_ratchet_config(RATCHET_CONFIG_PATH)
    violations = _collect_external_private_imports(src_dir, source_ast_cache)
    payload = {
        "max_count": int(config["max_count"]),
        "allowlist_count": len(ALLOWED_BASELINE_IMPORTS),
        "observed_count": len(violations),
        "unexpected": [
            {"importer": path, "target": module}
            for path, module in sorted(frozenset(violations) - ALLOWED_BASELINE_IMPORTS)
        ],
        "unused_allowlist": [
            {"importer": path, "target": module}
            for path, module in sorted(ALLOWED_BASELINE_IMPORTS - frozenset(violations))
        ],
    }
    errors = evaluate_ratchet(payload)
    assert not errors, "\n".join(errors)
    assert int(config["max_count"]) <= 19
    stale_waves = {
        str(row.get("target_removal_wave"))
        for row in config.get("pairs", [])
        if isinstance(row, dict)
    } & {f"S{i}" for i in range(1, 10)}
    assert not stale_waves, (
        "#9626: target_removal_wave must not keep closed S1–S9 tags; "
        f"found {sorted(stale_waves)}"
    )


@pytest.mark.architecture
def test_interfaces_do_not_import_private_composition_modules() -> None:
    """#9598: CLI must not import bioetl.composition._* implementation modules."""
    root = Path("src/bioetl/interfaces")
    hits: list[str] = []
    for py_file in root.rglob("*.py"):
        for lineno, line in enumerate(
            py_file.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if "bioetl.composition._" in line:
                hits.append(f"{py_file.as_posix()}:{lineno}:{line.strip()}")
    assert not hits, "interfaces imported private composition modules:\n" + "\n".join(
        hits
    )
