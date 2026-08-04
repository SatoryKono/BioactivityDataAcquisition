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
"""Architecture guards for tech-debt roadmap issues #7461–#7465."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.engineering.qa.report_debt_governance_gates import (
    DEBT_GATE_INPUT_ARTIFACTS,
)
from scripts.engineering.qa.refresh_governance_artifacts import _run_refresh
from tests.architecture._live_residual import (
    assert_residual_not_grown,
    load_live_residual_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
RETAINED_PLAN = (
    ROOT / "reports" / "quality" / "retained-public-entrypoint-burn-down-plan.json"
)
ZERO_REF_REVIEW = (
    ROOT / "reports" / "quality" / "zero-ref-supporting-scripts-review-20260804.json"
)
CLOSEOUT_FOLD = (
    ROOT / "reports" / "quality" / "closeout-freeze-fold-progress-20260804.json"
)
FACADE_INVENTORY = ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
SCRIPTS_MANIFEST = ROOT / "configs" / "quality" / "scripts_inventory_manifest.json"
DEBT_PLAYBOOK = (
    ROOT / "docs" / "00-project" / "governance" / "08-debt-ownership-playbook.md"
)
REFRESH_MODULE = (
    ROOT / "scripts" / "engineering" / "qa" / "refresh_governance_artifacts.py"
)
GATES_MODULE = (
    ROOT / "scripts" / "engineering" / "qa" / "report_debt_governance_gates.py"
)

pytestmark = pytest.mark.architecture


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_retained_entrypoint_burn_down_plan_covers_inventory_paths() -> None:
    """#7461: burn-down plan must cover every retained entrypoint (no silent drops)."""
    plan = _load_json(RETAINED_PLAN)
    inventory = cast(
        dict[str, Any],
        yaml.safe_load(FACADE_INVENTORY.read_text(encoding="utf-8")),
    )
    retained = inventory.get("retained_entrypoints") or []
    assert isinstance(retained, list)
    inventory_paths = {
        str(row["path"]) for row in retained if isinstance(row, dict) and "path" in row
    }
    plan_paths = {
        str(row["path"])
        for row in plan.get("surfaces") or []
        if isinstance(row, dict) and "path" in row
    }
    assert plan["linked_issue"] == "#7461"
    assert plan["wave"]["removal_candidates"] == []
    assert plan_paths == inventory_paths
    assert all(
        str(row.get("decision")) == "keep"
        for row in plan.get("surfaces") or []
        if isinstance(row, dict)
    )
    assert plan["policy"]["silent_removal"] == "forbidden"


def test_zero_ref_supporting_scripts_review_covers_manifest_zero_refs() -> None:
    """#7463: review artifact must list every inventory zero-ref supporting script."""
    review = _load_json(ZERO_REF_REVIEW)
    manifest = _load_json(SCRIPTS_MANIFEST)
    scripts = manifest.get("scripts") or []
    assert isinstance(scripts, list)
    zero_paths = {
        str(row["path"])
        for row in scripts
        if isinstance(row, dict)
        and row.get("status") == "supporting"
        and int(row.get("reference_count") or 0) == 0
    }
    review_paths = {
        str(row["path"])
        for row in review.get("scripts") or []
        if isinstance(row, dict) and "path" in row
    }
    assert review["linked_issue"] == "#7463"
    assert review_paths == zero_paths
    assert int(review["summary"]["delete_count"]) == 0
    assert int(review["summary"]["retain_count"]) == len(zero_paths)
    for row in review.get("scripts") or []:
        if not isinstance(row, dict):
            continue
        assert row.get("decision") == "retain"
        proof = row.get("importer_proof")
        assert isinstance(proof, dict)
        assert proof.get("method")


def test_closeout_fold_progress_and_live_residual_closeout_program() -> None:
    """#7464: fold progress + live residual closeout_program residual freezes."""
    progress = _load_json(CLOSEOUT_FOLD)
    residual = load_live_residual_snapshot()
    program = residual.get("closeout_program")
    assert isinstance(program, dict)
    assert progress["linked_issue"] == "#7464"
    assert progress["parent_issue"] == "#6891"
    assert (
        progress["snapshot_artifact"] == "reports/quality/live-residual-snapshot.json"
    )

    arch = ROOT / "tests" / "architecture"
    live_closeout_files = len(list(arch.glob("test_tech_debt*closeout*.py")))
    assert_residual_not_grown(
        metric_name="closeout_program.tech_debt_closeout_test_file_count",
        live_value=live_closeout_files,
        baseline_value=int(program["tech_debt_closeout_test_file_count"]),
    )
    inventory = cast(
        dict[str, Any],
        yaml.safe_load(FACADE_INVENTORY.read_text(encoding="utf-8")),
    )
    retained = inventory.get("retained_entrypoints") or []
    assert isinstance(retained, list)
    assert_residual_not_grown(
        metric_name="closeout_program.retained_public_entrypoint_count",
        live_value=len(retained),
        baseline_value=int(program["retained_public_entrypoint_count"]),
    )
    manifest = _load_json(SCRIPTS_MANIFEST)
    zero_ref = sum(
        1
        for row in manifest.get("scripts") or []
        if isinstance(row, dict)
        and row.get("status") == "supporting"
        and int(row.get("reference_count") or 0) == 0
    )
    assert_residual_not_grown(
        metric_name="closeout_program.zero_reference_supporting_script_count",
        live_value=zero_ref,
        baseline_value=int(program["zero_reference_supporting_script_count"]),
    )


def test_debt_gate_input_set_documented_and_refresh_ends_with_gates_update() -> None:
    """#7465: gate input set is explicit; refresh recipe regenerates gates last."""
    assert DEBT_GATE_INPUT_ARTIFACTS
    for rel in DEBT_GATE_INPUT_ARTIFACTS:
        assert (ROOT / rel).exists() or rel.endswith(".json"), rel

    gates_src = GATES_MODULE.read_text(encoding="utf-8")
    assert "DEBT_GATE_INPUT_ARTIFACTS" in gates_src
    assert "#7465" in gates_src

    refresh_src = REFRESH_MODULE.read_text(encoding="utf-8")
    # Gates --update must appear after scorecard refresh (last quality rollup).
    scorecard_pos = refresh_src.rfind("report_architecture_quality_scorecard")
    gates_pos = refresh_src.rfind("report_debt_governance_gates")
    assert scorecard_pos != -1 and gates_pos != -1
    assert gates_pos > scorecard_pos
    assert '"--update"' in refresh_src or "'--update'" in refresh_src
    # Ensure _run_refresh is still the active refresh path.
    assert callable(_run_refresh)


def test_debt_playbook_declares_tech_debt_pr_quality_artifact_scope() -> None:
    """#7462: debt ownership playbook documents quality-artifact PR scope."""
    text = DEBT_PLAYBOOK.read_text(encoding="utf-8")
    assert "#7462" in text
    assert "Tech-debt PR path scope" in text
    assert "configs/quality/**" in text
    assert "reports/quality/**" in text
    assert "scripts/ai/mcp/**" in text
    assert "refresh_governance_artifacts" in text
