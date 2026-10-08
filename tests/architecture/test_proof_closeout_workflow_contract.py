"""CI closeout consumes complete producer evidence without repeating test commands."""

from __future__ import annotations

from pathlib import Path
from collections import Counter

import pytest
import yaml

from scripts.engineering.qa.run_local_coverage_verify import SHARDS

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]


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
    config = yaml.safe_load(
        (ROOT / ".circleci/config.yml").read_text(encoding="utf-8")
    )
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
    assert "setup_grafana_screenshot_runtime.sh --attempt-system-install" in browser_setup
    assert any("actual == locked" in command for command in commands)


def test_rf023_full_suite_receipt_binds_junit_and_isolates_selection():
    config = yaml.safe_load(
        (ROOT / ".circleci/config.yml").read_text(encoding="utf-8")
    )
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
