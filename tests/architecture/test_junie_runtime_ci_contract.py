"""CI linkage guards for the tracked Codex–Junie runtime parity contract."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import re
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "skills-consistency.yml"
CONTRACT_PATH = ROOT / "scripts" / "ai" / "junie" / "junie-mirror-contract.json"
JUNIE_RUNTIME_PATH = ROOT / ".junie" / "agents" / "JUNIE-RUNTIME.md"
JUNIE_GUIDELINES_PATH = ROOT / ".junie" / "guidelines.md"


def _workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_skills_consistency_watches_runtime_parity_surfaces() -> None:
    """Runtime parity surfaces stay guarded after the coordinator cutover.

    Leaf Actions workflows no longer carry push/pull_request path filters;
    the CircleCI ``skills-consistency`` job runs the canonical mirror checks
    inside ``pr-gate`` on every gated run.
    """
    config = yaml.safe_load(
        (ROOT / ".circleci" / "config.yml").read_text(encoding="utf-8")
    )
    job = config["jobs"]["skills-consistency"]
    commands = " ".join(
        step["run"]["command"]
        for step in job["steps"]
        if isinstance(step, dict) and isinstance(step.get("run"), dict)
    )
    for check in (
        "bash scripts/ai/junie/check_junie_mirror.sh --check",
        "bash scripts/ops/support/skills/check_skills_mirror.sh --check",
        "bash scripts/ops/support/skills/check_ai_skills_layout.sh",
        "python -m scripts.ai.sync.runtime_skills",
    ):
        assert check in commands
    pr_gate_jobs = config["workflows"]["pr-gate"]["jobs"]
    assert any(
        isinstance(entry, dict) and "skills-consistency" in entry
        for entry in pr_gate_jobs
    )


def test_skills_consistency_executes_canonical_junie_checker() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    job = jobs["verify-codex-junie-runtime-parity"]
    commands = [step.get("run", "") for step in job["steps"] if isinstance(step, dict)]
    assert "bash scripts/ai/junie/check_junie_mirror.sh --check" in commands


def test_junie_runtime_maps_exact_codex_profile_inventory() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    excluded = set(contract["parity_scope"]["agents"]["exclude_filenames"])
    expected = {
        path.stem
        for path in (ROOT / ".codex" / "agents").glob("py-*.md")
        if path.name not in excluded
    }
    runtime = JUNIE_RUNTIME_PATH.read_text(encoding="utf-8")
    mapped = set(
        re.findall(r"^\|\s*`(py-[a-z0-9-]+)`\s*\|", runtime, flags=re.MULTILINE)
    )

    assert mapped == expected


def test_junie_dashboard_routing_uses_active_observability_skills() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    semantics = contract["runtime_semantics"]
    runtime = JUNIE_RUNTIME_PATH.read_text(encoding="utf-8")
    guidelines = JUNIE_GUIDELINES_PATH.read_text(encoding="utf-8")

    for skill_name in semantics["required_dashboard_skills"]:
        assert f".junie/skills/{skill_name}/" in guidelines
    plan_texts = [
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / ".junie" / "plans").rglob("*.md"))
    ]
    for identifier in semantics["forbidden_identifiers"]:
        assert identifier not in runtime
        assert identifier not in guidelines
        for plan_text in plan_texts:
            assert identifier not in plan_text


def test_junie_guidelines_include_environment_configuration() -> None:
    """AGENTS.md and Junie guidelines must share the .env token contract (#9120)."""
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    guidelines = JUNIE_GUIDELINES_PATH.read_text(encoding="utf-8")
    for content in (agents, guidelines):
        assert "## Environment Configuration" in content
        assert "MUST use tokens and parameters from the repository root" in content


def test_junie_guidelines_include_full_tree_commits() -> None:
    """Junie Guardrails must mirror the full-tree commit gate (#11709/#11786)."""
    guidelines = JUNIE_GUIDELINES_PATH.read_text(encoding="utf-8")
    assert "Full-tree commits only" in guidelines
    assert "check_no_partial_tree.py" in guidelines


def test_manual_runtime_closeout_uses_existing_producers_and_real_source() -> None:
    job = _workflow()["jobs"]["verify-native-codex-runtime"]
    steps = {step["name"]: step for step in job["steps"]}
    capture = steps["Capture source-bound runtime closeout"]
    assert (
        capture["if"]
        == "github.event_name == 'workflow_dispatch' && !inputs.approve_runtime_sync"
    )
    command = capture["run"]
    for required in (
        'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
        "capture tests test_health tests python -m pytest",
        "capture governance pretest_guardrails governance bash",
        "capture docs docs_runtime_checks docs_runtime python -m scripts.docs check-links",
        "capture debt debt_governance_gates debt python -m scripts.engineering.qa",
        "proof-or-stop",
        '"${proof[@]}" assemble',
        '"${proof[@]}" verify --bundle',
        "rc=$?",
        "state=fail",
        '--status "$state" --exit-code "$rc"',
    ):
        assert required in command
    assert "--no-source-check" not in command
    assert "proof-or-stop ingest" not in command
    assert job["timeout-minutes"] == 5
    assert steps["Checkout code"]["with"]["fetch-depth"] == 0
    assert (
        steps["Upload explicit manual closeout evidence"]["with"]["if-no-files-found"]
        == "error"
    )


@pytest.mark.parametrize("exit_code,expected", [(0, "pass"), (7, "fail")])
def test_manual_capture_preserves_actual_command_failure(
    tmp_path: Path, exit_code: int, expected: str
) -> None:
    bash = shutil.which("bash")
    if os.name == "nt":
        git = shutil.which("git")
        candidate = Path(git).resolve().parent.parent / "bin/bash.exe" if git else None
        bash = str(candidate) if candidate and candidate.is_file() else None
    if bash is None:
        pytest.skip("native Bash is unavailable; CI capture is Linux-qualified only")
    step = next(
        item
        for item in _workflow()["jobs"]["verify-native-codex-runtime"]["steps"]
        if item["name"] == "Capture source-bound runtime closeout"
    )
    source = step["run"]
    start = source.index("capture() {")
    end = source.index("\n}", start) + 2
    function = source[start:end]
    directory = shlex.quote(tmp_path.as_posix())
    script = tmp_path / "capture-fixture.sh"
    script.write_text(
        "set -euo pipefail\n"
        f"run_dir={directory}\n"
        "common=()\n"
        'record_receipt() { printf "%s\\0" "$@" > "$run_dir/receipt.args"; }\n'
        "proof=(record_receipt)\n"
        'uv() { shift 4; "$@"; }\n'
        + function
        + "\n"
        + f"capture fixture test_health tests bash -c 'exit {exit_code}'\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [bash, "--noprofile", "--norc", script.as_posix()],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    args = (tmp_path / "receipt.args").read_bytes().decode().split("\0")
    assert args[args.index("--status") + 1] == expected
    assert args[args.index("--exit-code") + 1] == str(exit_code)
    assert int(args[args.index("--duration-ms") + 1]) >= 0
