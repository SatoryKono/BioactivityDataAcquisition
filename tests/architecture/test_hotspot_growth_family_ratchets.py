"""Architecture guardrails for active hotspot-family file-growth budgets."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.qa.hotspot_family_metrics import count_files_ge_loc

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
_ENFORCED_RATCHET_STAGES = {"active", "reviewed-baseline"}


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
        and family.get("ratchet_stage") in _ENFORCED_RATCHET_STAGES
        and isinstance(family.get("bounded_growth_budgets"), dict)
        and "files_ge_250_loc" in family["bounded_growth_budgets"]
    ]
    assert budgeted_families, (
        "Expected at least one enforced hotspot family with a growth budget"
    )

    for family in budgeted_families:
        family_name = family.get("name")
        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(path_prefixes, list) and path_prefixes
        files = _iter_family_python_files(
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ]
        )
        actual_count = count_files_ge_loc(files=files, min_lines=250)
        budget = family["bounded_growth_budgets"].get("files_ge_250_loc")
        assert isinstance(budget, int) and budget >= 0
        assert actual_count <= budget, (
            f"Hotspot family {family_name} has {actual_count} files >= 250 LOC, "
            f"exceeding bounded budget {budget}. Keep the composition/file-growth "
            "ratchet stable or intentionally refresh the reviewed hotspot-family "
            "baseline."
        )


def test_refactored_hotspot_module_line_budgets_hold() -> None:
    """Recently split hotspot modules must not grow back into orchestration blobs."""
    module_budgets = {
        "src/bioetl/composition/runtime_builders/runner_builder.py": 200,
        "src/bioetl/composition/runtime_builders/runner_control_plane_assembly.py": 180,
        "src/bioetl/application/services/control_plane/run_manifest_exact_replay_blockers.py": 120,
        "src/bioetl/application/composite/runner_pkg/runner_execution_orchestrator.py": 220,
    }

    for rel_path, max_lines in module_budgets.items():
        actual_lines = len(
            (PROJECT_ROOT / rel_path).read_text(encoding="utf-8").splitlines()
        )
        assert actual_lines <= max_lines, (
            f"{rel_path} has {actual_lines} lines, exceeding ratcheted budget "
            f"{max_lines}. Extract a focused helper/service instead of regrowing "
            "the hotspot module."
        )
