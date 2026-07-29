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
"""Architecture checks for committed CI test telemetry baselines."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
BASELINE_YAML = ROOT / "configs" / "quality" / "test_telemetry_baseline.yaml"
BASELINE_MD = ROOT / "docs" / "05-engineering" / "test-telemetry-baseline.md"
ENGINEERING_README = ROOT / "docs" / "05-engineering" / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
SLOWEST_JSON = ROOT / "reports" / "test-telemetry" / "slowest-tests.json"
SLOWEST_MD = ROOT / "reports" / "test-telemetry" / "slowest-tests.md"
COVERAGE_SUMMARY_JSON = ROOT / "reports" / "test-telemetry" / "coverage-summary.json"


def _load_yaml(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_test_telemetry_baseline_contract_is_present_and_scoped() -> None:
    payload = _load_yaml(BASELINE_YAML)

    assert payload["policy_scope"] == "test_telemetry_baseline"
    assert payload["workflow_path"] == ".github/workflows/tests.yml"
    assert payload["source_branch"] == "main"
    assert payload["artifact_inputs"]["coverage_xml"] == "reports/coverage/coverage.xml"
    assert (
        payload["artifact_inputs"]["slowest_tests_json"]
        == "reports/test-telemetry/slowest-tests.json"
    )
    assert payload["coverage"]["threshold_percent"] == pytest.approx(85.0)
    assert payload["freshness_guard"]["timestamp_field"] == "refreshed_at_utc"
    assert int(payload["freshness_guard"]["max_age_days"]) > 0


def test_test_telemetry_baseline_doc_is_published_from_engineering_index() -> None:
    assert BASELINE_MD.exists()
    readme = ENGINEERING_README.read_text(encoding="utf-8")
    assert "test-telemetry-baseline.md" in readme


def test_branch_consumable_test_telemetry_reports_exist() -> None:
    assert SLOWEST_JSON.exists()
    assert SLOWEST_MD.exists()
    assert COVERAGE_SUMMARY_JSON.exists()


def test_tests_workflow_and_baseline_contract_use_same_artifact_paths() -> None:
    payload = _load_yaml(BASELINE_YAML)
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert payload["artifact_inputs"]["coverage_xml"] in workflow
    assert payload["artifact_inputs"]["slowest_tests_json"] in workflow
    assert "name: test-duration-telemetry" in workflow
    assert "coverage xml -o reports/coverage/coverage.xml" in workflow
