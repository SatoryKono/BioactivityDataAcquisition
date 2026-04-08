"""Architecture guardrails for active hotspot-family internal fan-in budgets."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
SRC_ROOT = PROJECT_ROOT / "src" / "bioetl"


def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _module_name_from_path(path: Path) -> str:
    rel = path.relative_to(SRC_ROOT)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = Path(parts[-1]).stem
    return ".".join(["bioetl", *parts]) if parts else "bioetl"


def _iter_family_python_files(*, path_prefixes: list[str]) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for prefix in path_prefixes:
        root = PROJECT_ROOT / prefix
        for path in sorted(root.rglob("*.py")):
            if path in seen:
                continue
            seen.add(path)
            files.append(path)
    return files


def _resolve_relative_import_base(source_module: str, level: int) -> list[str]:
    package_parts = source_module.split(".")[:-1]
    depth = max(level - 1, 0)
    if depth > len(package_parts):
        return []
    if depth == 0:
        return package_parts
    return package_parts[:-depth]


def _resolve_internal_import_targets(
    node: ast.Import | ast.ImportFrom,
    *,
    source_module: str,
    family_modules: set[str],
) -> tuple[str, ...]:
    targets: list[str] = []

    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name in family_modules:
                targets.append(alias.name)
        return tuple(targets)

    if node.level == 0:
        if not node.module:
            return ()
        base_module = node.module
    else:
        base_parts = _resolve_relative_import_base(source_module, node.level)
        if not base_parts:
            return ()
        base_module = ".".join([*base_parts, node.module]) if node.module else ".".join(
            base_parts
        )

    for alias in node.names:
        if alias.name == "*":
            continue
        candidate = f"{base_module}.{alias.name}"
        if candidate in family_modules:
            targets.append(candidate)
            continue
        if base_module in family_modules:
            targets.append(base_module)

    if not targets and base_module in family_modules:
        targets.append(base_module)
    return tuple(targets)


def _count_internal_fan_in(*, files: list[Path]) -> tuple[int, str | None]:
    module_map = {_module_name_from_path(path): path for path in files}
    family_modules = set(module_map)
    fan_in_counter: Counter[str] = Counter()

    for source_module, path in module_map.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        seen_targets: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            seen_targets.update(
                _resolve_internal_import_targets(
                    node,
                    source_module=source_module,
                    family_modules=family_modules,
                )
            )

        for target in seen_targets:
            if target == source_module:
                continue
            fan_in_counter[target] += 1

    if not fan_in_counter:
        return 0, None

    max_module, max_fan_in = max(
        fan_in_counter.items(),
        key=lambda item: (item[1], item[0]),
    )
    return max_fan_in, max_module


def test_active_hotspot_family_internal_fan_in_budgets_hold_reviewed_baseline() -> None:
    """Selected active hotspot families must not exceed their internal fan-in cap."""
    scorecard = _load_scorecard()
    hotspot_policy = scorecard.get("report_only_hotspot_families", {})
    assert isinstance(hotspot_policy, dict)

    families = hotspot_policy.get("families", [])
    assert isinstance(families, list) and families

    budgeted_families = [
        family
        for family in families
        if isinstance(family, dict)
        and family.get("ratchet_stage") == "active"
        and isinstance(family.get("bounded_growth_budgets"), dict)
        and "max_internal_fan_in" in family["bounded_growth_budgets"]
    ]
    assert budgeted_families, "Expected at least one active family with a fan-in budget"

    for family in budgeted_families:
        family_name = family.get("name")
        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(path_prefixes, list) and path_prefixes
        files = _iter_family_python_files(
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ]
        )
        actual_fan_in, actual_module = _count_internal_fan_in(files=files)
        budget = family["bounded_growth_budgets"].get("max_internal_fan_in")
        assert isinstance(budget, int) and budget >= 0
        assert actual_fan_in <= budget, (
            f"Hotspot family {family_name} has max_internal_fan_in={actual_fan_in} "
            f"at module {actual_module}, exceeding bounded budget {budget}. "
            "Keep the family dependency ratchet stable or rebaseline the reviewed "
            "scorecard snapshot intentionally under RF-06."
        )
