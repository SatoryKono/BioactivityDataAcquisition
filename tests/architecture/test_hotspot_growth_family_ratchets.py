"""Architecture guardrails for active hotspot-family file-growth budgets."""

from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"


def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


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


def _count_files_ge_loc(*, files: list[Path], min_lines: int) -> int:
    return sum(
        1
        for path in files
        if len(path.read_text(encoding="utf-8").splitlines()) >= min_lines
    )


def test_active_hotspot_family_file_growth_budgets_hold_reviewed_baseline() -> None:
    """Selected active hotspot families must not exceed their bounded file-growth cap."""
    scorecard = _load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)

    families = hotspot_policy.get("families", [])
    assert isinstance(families, list) and families

    budgeted_families = [
        family
        for family in families
        if isinstance(family, dict)
        and family.get("ratchet_stage") == "active"
        and isinstance(family.get("bounded_growth_budgets"), dict)
        and "files_ge_250_loc" in family["bounded_growth_budgets"]
    ]
    assert budgeted_families, "Expected at least one active family with a growth budget"

    for family in budgeted_families:
        family_name = family.get("name")
        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(path_prefixes, list) and path_prefixes
        files = _iter_family_python_files(
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ]
        )
        actual_count = _count_files_ge_loc(files=files, min_lines=250)
        budget = family["bounded_growth_budgets"].get("files_ge_250_loc")
        assert isinstance(budget, int) and budget >= 0
        assert actual_count <= budget, (
            f"Hotspot family {family_name} has {actual_count} files >= 250 LOC, "
            f"exceeding bounded budget {budget}. Keep the composition/file-growth "
            "ratchet stable or rebaseline the reviewed scorecard snapshot intentionally."
        )
