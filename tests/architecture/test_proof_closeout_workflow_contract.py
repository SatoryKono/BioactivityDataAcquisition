"""CI closeout consumes complete producer evidence without repeating test commands."""

from __future__ import annotations

from pathlib import Path
from collections import Counter

import pytest
import yaml

from scripts.engineering.ci.closeout_cost_budget import evaluate_closeout_cost_budget
from scripts.engineering.qa.run_local_coverage_verify import SHARDS

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
BUDGET = ROOT / "configs/quality/ci_closeout_cost_budget.yaml"
TELEMETRY = ROOT / "configs/quality/test_telemetry_baseline.yaml"


def test_rf023_keeps_its_own_task_identity_and_branch():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load(
        (ROOT / "configs/quality/proof_closeout_checks.yaml").read_text()
    )
    job = config["workflows"]["rf023-closeout"]["jobs"][0]["rf023-proof-closeout"]
    assert job["task-id"] == "rf023-11906-11907"
    branches = job["filters"]["branches"]["only"]
    assert branches == [
        "codex/pipeline-green-gates-rf022-snapshot-fix",
        "codex/issue-11907-rf023-closeout-20261007",
    ]
    assert job["task-id"] != catalog["task_id"]
    assert set(branches).isdisjoint(catalog["branches"])
    assert "task-id" in config["jobs"]["rf023-proof-closeout"]["parameters"]


def test_all_coverage_shards_have_one_owner():
    catalog = yaml.safe_load(
        (ROOT / "configs/quality/proof_closeout_checks.yaml").read_text()
    )
    selected = []
    for name, spec in catalog["checks"].items():
        if name.startswith("coverage-"):
            args = spec["argv"]
            selected.extend(
                args[i + 1] for i, arg in enumerate(args) if arg == "--shard"
            )
    assert Counter(selected) == Counter(s.name for s in SHARDS)
    assert "--merge-dir" in catalog["checks"]["coverage"]["argv"]


def test_coverage_closeout_respects_shrink_only_ci_cost_budget():
    catalog = yaml.safe_load(
        (ROOT / "configs/quality/proof_closeout_checks.yaml").read_text()
    )
    budget = yaml.safe_load(BUDGET.read_text(encoding="utf-8"))
    telemetry = yaml.safe_load(TELEMETRY.read_text(encoding="utf-8"))
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))

    assert budget["schema_version"] == 1
    assert budget["policy_scope"] == "ci_closeout_cost_budget"
    assert budget["budget_policy"] == "shrink_only"
    assert budget["baseline"]["source_commit"] == telemetry["source_commit"]
    assert (
        budget["baseline"]["test_tree_sha256"]
        == telemetry["measurement_provenance"]["test_tree_sha256"]
    )

    limits = budget["limits"]
    assert limits["coverage_job_count"] == 4
    assert limits["additional_coverage_jobs"] == 0
    assert limits["coverage_resource_class"] == "medium"
    assert limits["resource_class_increase_allowed"] is False
    assert config["jobs"]["proof-coverage-shard"]["resource_class"] == "medium"

    lane_seconds = telemetry["duration_telemetry"]["execution_context"][
        "lane_wall_time_s"
    ]
    group_seconds = []
    selected = []
    for index in range(limits["coverage_job_count"]):
        args = catalog["checks"][f"coverage-{index}"]["argv"]
        shards = [args[i + 1] for i, arg in enumerate(args) if arg == "--shard"]
        selected.extend(shards)
        group_seconds.append(round(sum(lane_seconds[name] for name in shards), 2))

    assert Counter(selected) == Counter(shard.name for shard in SHARDS)
    assert round(sum(group_seconds), 2) <= limits["total_lane_seconds"]
    assert max(group_seconds) <= limits["critical_path_seconds"]
    assert limits["total_lane_seconds"] <= budget["baseline"]["total_lane_seconds"]
    assert limits["critical_path_seconds"] < budget["baseline"]["critical_path_seconds"]

    for workflow in (
        "pr-gate",
        "main-coverage-closeout",
        "migration-coverage-closeout",
    ):
        matrix = next(
            item["proof-coverage-shard"]["matrix"]["parameters"]["group"]
            for item in config["workflows"][workflow]["jobs"]
            if isinstance(item, dict) and "proof-coverage-shard" in item
        )
        assert matrix == ["0", "1", "2", "3"]


def test_runtime_closeout_cost_budget_is_admissible():
    result = evaluate_closeout_cost_budget(ROOT)

    assert result["outcome"] == "PASS", result["errors"]
    assert result["measurements"] == {
        "coverage_job_count": 4,
        "coverage_resource_class": "medium",
        "group_seconds": {
            "0": 535.54,
            "1": 535.39,
            "2": 534.31,
            "3": 533.84,
        },
        "total_lane_seconds": 2139.08,
        "critical_path_seconds": 535.54,
    }


def test_proof_jobs_measure_executor_time_without_an_extra_job():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    budget = yaml.safe_load(BUDGET.read_text(encoding="utf-8"))
    command = budget["runtime_measurement"]["start_command"]

    assert budget["runtime_measurement"]["additional_telemetry_jobs"] == 0
    assert command in config["commands"]
    for job_name in (
        "arch-tests",
        "proof-coverage",
        "proof-governance",
        "proof-debt",
        "proof-quality",
        "proof-closeout",
        "proof-docs",
        "proof-coverage-shard",
    ):
        assert config["jobs"][job_name]["steps"][0] == command


def test_proof_waits_for_producers_in_the_same_workflow():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    for workflow in (
        "pr-gate",
        "main-coverage-closeout",
        "migration-coverage-closeout",
    ):
        jobs = config["workflows"][workflow]["jobs"]
        by_name = {
            next(iter(j)): next(iter(j.values())) for j in jobs if isinstance(j, dict)
        }
        assert set(by_name["proof-closeout"]["requires"]) == {
            "arch-tests",
            "docs-governance" if workflow == "pr-gate" else "proof-docs",
            "proof-governance",
            "proof-debt",
            "proof-quality",
        }
        assert set(by_name["proof-quality"]["requires"]) == {
            "proof-coverage",
            "arch-tests",
        }
        assert by_name["proof-coverage"]["requires"] == ["proof-coverage-shards"]
    closeout = config["jobs"]["proof-closeout"]
    commands = "\n".join(
        s["run"]["command"]
        for s in closeout["steps"]
        if isinstance(s, dict) and "run" in s
    )
    assert "proof-or-stop ci assemble" in commands
    assert "pytest" not in commands
    assert "run_local_coverage_verify" not in commands
    assert "produce --check" not in commands


def test_full_architecture_and_branch_activation_are_preserved():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load(
        (ROOT / "configs/quality/proof_closeout_checks.yaml").read_text()
    )
    argv = catalog["checks"]["architecture"]["argv"]
    assert "tests/architecture" in argv
    assert "-m" not in argv[argv.index("pytest") + 1 :]
    assert "--no-cov" in argv
    jobs = config["workflows"]["pr-gate"]["jobs"]
    for item in jobs:
        if isinstance(item, dict) and next(iter(item)).startswith("proof-"):
            assert set(next(iter(item.values()))["filters"]["branches"]["only"]) == set(
                catalog["branches"]
            )


def test_rf023_requires_terminal_full_suite_and_preserves_ci_identity():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    job = config["jobs"]["rf023-proof-closeout"]
    commands = [
        s["run"]["command"] for s in job["steps"] if isinstance(s, dict) and "run" in s
    ]
    source = next(command for command in commands if "CLOSEOUT_PY" in command)
    assert '"scripts.engineering.dev", "run-tests", "all"' in source
    assert '"--vcr-record=none"' in source
    assert '"--junitxml=" + str(out / "full-suite.xml")' in source
    assert 'evidence_kind = "tests" if kind == "full-suite" else kind' in source
    assert '"--evidence-kind", evidence_kind' in source
    assert "ElementTree.parse(junit)" in source
    assert "assert cases and all" in source
    assert 'case.find("failure") is None and case.find("error") is None' in source
    assert 'assert os.environ.get("CIRCLECI") == "true"' in source
    assert 'assert os.environ.get("CIRCLE_SHA1") == head' in source
    assert 'assert manifest["complete"] is True and manifest["head"] == head' in source
    assert '"--trust-tier", "ci"' in source
    assert job["resource_class"] == "large"
    assert job["docker"][0]["image"] == "cimg/python:3.12-node"
    assert any(
        "command -v node" in command and "command -v npm" in command
        for command in commands
    )
    browser_setup = next(
        command
        for command in commands
        if "setup_grafana_screenshot_runtime.sh" in command
    )
    assert browser_setup.index("sudo apt-get update -qq") < browser_setup.index(
        "bash scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.sh"
    )
    assert (
        "setup_grafana_screenshot_runtime.sh --attempt-system-install" in browser_setup
    )
    assert any("actual == locked" in command for command in commands)


def test_rf023_full_suite_receipt_binds_junit_and_isolates_selection():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    source = next(
        s["run"]["command"]
        for s in config["jobs"]["rf023-proof-closeout"]["steps"]
        if isinstance(s, dict) and "run" in s and "CLOSEOUT_PY" in s["run"]["command"]
    )
    assert "unset BASH_ENV PYTEST_ADDOPTS" in source
    assert (
        'record["junit_sha256"] = hashlib.sha256(junit.read_bytes()).hexdigest()'
        in source
    )
    assert source.index("sanitize(junit)") < source.index('record["junit_sha256"]')
    assert 'record["log_sha256"]' in source
    assert '"--output-artifact", output_artifact' in source
    assert 'tempfile.mkdtemp(prefix=run_id + "-full-suite-")' in source
    assert '"--basetemp=" + str(full_suite_tmp)' in source


def test_diagram_drift_has_a_reachable_merge_base_before_diff():
    source = (ROOT / ".circleci/config.yml").read_text(encoding="utf-8")
    start = source.index("name: Canonical diagram drift validation")
    drift = source[start : source.index("changed_diagrams=$(", start)]
    assert "git fetch --no-tags --unshallow origin" in drift
    assert (
        'git fetch --no-tags origin "${BASE_REF}:refs/remotes/origin/${BASE_REF}"'
        in drift
    )
    assert 'git merge-base "${base_ref}" HEAD >/dev/null' in drift
    assert "--depth=1" not in drift
