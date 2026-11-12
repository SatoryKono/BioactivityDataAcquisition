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


from scripts.ai.junie import check_junie_mirror as mirror

OBLIGATIONS = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))[
    "guardrail_obligations"
]
check_obligations = mirror.check_obligations
guardrail_section = mirror.guardrail_section
normalize_clause = mirror.normalize_clause

SOURCE = ROOT


def _guardrail_fixture_tree(root: Path) -> None:
    for name in {p for item in OBLIGATIONS for p in item["paths"]}:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text((SOURCE / name).read_text(encoding="utf-8"), encoding="utf-8")


def test_current_variants_pass_without_writes_or_processes(tmp_path, monkeypatch):
    _guardrail_fixture_tree(tmp_path)
    monkeypatch.setattr(Path, "write_text", lambda *a, **k: pytest.fail("write"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("process"))
    assert check_obligations(tmp_path, OBLIGATIONS) == []


@pytest.mark.parametrize(
    "name",
    [
        "AGENTS.md",
        ".junie/guidelines.md",
        ".codex/agents/CODEX-RUNTIME.md",
        ".junie/agents/JUNIE-RUNTIME.md",
        ".devin/agents/DEVIN-RUNTIME.md",
    ],
)
def test_weakened_env_obligation_is_detected(tmp_path, name):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / name
    p.write_text(
        p.read_text(encoding="utf-8").replace("MUST NOT", "MAY"), encoding="utf-8"
    )
    assert any("env" in issue for issue in check_obligations(tmp_path, OBLIGATIONS))


@pytest.mark.parametrize(
    "old,new,obligation",
    [
        ("ЗАПРЕЩЕНО", "РАЗРЕШЕНО", "root-debt-tree"),
        ("| V3/V4 |", "| V5 |", "root-context"),
        ("After changes under", "Before optional changes under", "root-validation"),
        (
            "check_junie_mirror.py --check",
            "check_junie_mirror.py --sync",
            "root-validation",
        ),
        ("check_no_partial_tree.py", "unchecked_partial_tree.py", "root-debt-tree"),
        (
            "worktree-location restriction",
            "worktree-location preference",
            "worktree-user-scope",
        ),
        ("stay disabled", "may be enabled", "opencode-subordinate"),
    ],
)
def test_root_trigger_and_guard_mutations(tmp_path, old, new, obligation):
    _guardrail_fixture_tree(tmp_path)
    for name in ["AGENTS.md", ".junie/guidelines.md"]:
        p = tmp_path / name
        text = p.read_text(encoding="utf-8")
        assert old in text
        p.write_text(text.replace(old, new), encoding="utf-8")
    # Both governed copies can drift together; byte parity would not catch this.
    assert any(
        obligation in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


def test_root_authority_cannot_be_weakened(tmp_path):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / "AGENTS.md"
    text = p.read_text(encoding="utf-8")
    changed = re.sub(r"cannot\s+be\s+weakened", "may be weakened", text)
    assert changed != text
    p.write_text(changed, encoding="utf-8")
    assert any(
        "root-authority" in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


@pytest.mark.parametrize("marker", ["1.", "1)"])
def test_parallel_precedence_is_detected_in_owner_reference(tmp_path, marker):
    _guardrail_fixture_tree(tmp_path)
    name = "docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md"
    p = tmp_path / name
    text = p.read_text(encoding="utf-8")
    section = guardrail_section(text, "Precedence Model")
    p.write_text(
        text.replace(section, section + f"\n{marker} Runtime overrides root.\n", 1),
        encoding="utf-8",
    )
    assert any(
        "parallel precedence" in issue
        for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


def test_duplicate_protected_heading_is_not_accepted(tmp_path):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / "AGENTS.md"
    p.write_text(
        p.read_text(encoding="utf-8") + "\n## Env File Guardrail\nMAY write\n",
        encoding="utf-8",
    )
    assert any(
        "duplicate section" in issue
        for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


def test_legitimate_runtime_specific_sections_remain_allowed(tmp_path):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / ".junie/agents/JUNIE-RUNTIME.md"
    p.write_text(
        p.read_text(encoding="utf-8")
        + "\n## Platform observation\nIDE registration is NOT_PROVEN.\n",
        encoding="utf-8",
    )
    assert check_obligations(tmp_path, OBLIGATIONS) == []


@pytest.mark.parametrize(
    "name,old,new",
    [
        (
            ".codex/agents/CODEX-RUNTIME.md",
            "is the only outcome",
            "is an optional outcome",
        ),
        (
            ".junie/agents/JUNIE-RUNTIME.md",
            "is the only outcome",
            "is an optional outcome",
        ),
        (".devin/agents/DEVIN-RUNTIME.md", "Only `ADMIT`", "Optionally `ADMIT`"),
    ],
)
def test_proof_qualification_cannot_be_weakened(tmp_path, name, old, new):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / name
    text = p.read_text(encoding="utf-8")
    assert old in text
    p.write_text(text.replace(old, new), encoding="utf-8")
    assert any(
        "runtime-proof" in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


def test_implementation_fact_precedence_is_a_legitimate_separate_scope(tmp_path):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / "docs/00-project/ai/agents/guides/MEMORY_USAGE.md"
    text = p.read_text(encoding="utf-8")
    section = guardrail_section(text, "Implementation Fact Conflicts", 3)
    assert "1." in section
    assert check_obligations(tmp_path, OBLIGATIONS) == []


@pytest.mark.parametrize(
    "old,new,expected",
    [
        ("может только уменьшаться", "может увеличиваться", "root-debt-tree"),
        ("src/bioetl/**/*.py", "src/bioetl/*.py", "root-validation"),
        (
            "never expands user authority",
            "may expand user authority",
            "worktree-user-scope",
        ),
    ],
)
def test_qualifier_and_glob_weakening_cannot_hide_behind_retained_keywords(
    tmp_path, old, new, expected
):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / "AGENTS.md"
    text = p.read_text(encoding="utf-8")
    assert old in text
    p.write_text(text.replace(old, new), encoding="utf-8")
    assert any(expected in issue for issue in check_obligations(tmp_path, OBLIGATIONS))


def test_markdown_normalization_preserves_technical_globs():
    assert normalize_clause("**MUST NOT** write `src/**/*.py`") == normalize_clause(
        "MUST NOT write `src/**/*.py`"
    )
    assert normalize_clause("MUST NOT write `src/**/*.py`") != normalize_clause(
        "MUST NOT write `src/*.py`"
    )


def test_quoted_rule_example_does_not_satisfy_guardrail(tmp_path):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / "AGENTS.md"
    text = p.read_text(encoding="utf-8")
    section = guardrail_section(text, "Env File Guardrail")
    assert section is not None
    quoted = "\n".join("> " + line for line in section.splitlines())
    p.write_text(text.replace(section, "\n" + quoted + "\n", 1), encoding="utf-8")
    assert any(
        "root-env" in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


@pytest.mark.parametrize("mutation", ["weaken", "comment", "fence"])
def test_devin_qualification_gate_is_authoritative(tmp_path, mutation):
    _guardrail_fixture_tree(tmp_path)
    p = tmp_path / ".devin/agents/DEVIN-RUNTIME.md"
    text = p.read_text(encoding="utf-8")
    section = guardrail_section(text, "Permission boundary and qualification")
    assert section is not None
    if mutation == "weaken":
        changed = section.replace("is blocked until", "may run before")
    elif mutation == "comment":
        changed = "\n<!--\n" + section + "\n-->\n"
    else:
        changed = "\n```markdown\n" + section + "\n```\n"
    p.write_text(text.replace(section, changed, 1), encoding="utf-8")
    assert any(
        "devin-native-qualification" in issue
        for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


@pytest.mark.parametrize(
    "old,new,identifier",
    [
        ("do not create root-level", "may create root-level", "root-local-safety"),
        (
            "unless the task explicitly requires them",
            "without task-specific need",
            "root-local-safety",
        ),
        (
            "Gemini is not a project runtime",
            "Gemini is a project runtime",
            "root-runtime-identity",
        ),
        (
            "MUST NOT be silently replaced",
            "MAY be silently replaced",
            "root-runtime-identity",
        ),
    ],
)
def test_local_safety_and_runtime_identity_cannot_weaken(
    tmp_path, old, new, identifier
):
    _guardrail_fixture_tree(tmp_path)
    for name in ("AGENTS.md", ".junie/guidelines.md"):
        p = tmp_path / name
        text = p.read_text(encoding="utf-8")
        assert old in text
        p.write_text(text.replace(old, new), encoding="utf-8")
    assert any(
        identifier in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


@pytest.mark.parametrize("invalid", [None, [], [{}], [{"id": "only-id"}]])
def test_guardrail_schema_fails_closed(invalid: Any) -> None:
    assert check_obligations(ROOT, invalid)


def test_guardrail_required_id_cannot_disappear() -> None:
    assert check_obligations(ROOT, OBLIGATIONS[1:]) == [
        "missing required guardrail obligation IDs"
    ]


def test_guardrail_duplicate_id_is_rejected() -> None:
    assert check_obligations(ROOT, [*OBLIGATIONS, OBLIGATIONS[0]]) == [
        "duplicate guardrail obligation IDs"
    ]


@pytest.mark.parametrize("path", ["../outside.md", ".env.example", "nested/.ENV.local"])
def test_guardrail_refuses_external_or_protected_sources(path: str) -> None:
    data = json.loads(json.dumps(OBLIGATIONS))
    data[0]["paths"] = [path]
    assert any("protected/external" in issue for issue in check_obligations(ROOT, data))


@pytest.mark.parametrize(
    "wrapper", ["<!--\n{}\n-->", "```markdown\n{}\n```", "<!--\n{}"]
)
def test_guardrail_comment_or_example_is_not_authoritative(
    tmp_path: Path, wrapper: str
) -> None:
    _guardrail_fixture_tree(tmp_path)
    path = tmp_path / "AGENTS.md"
    text = path.read_text(encoding="utf-8")
    section = guardrail_section(text, "Env File Guardrail")
    assert section is not None
    path.write_text(
        text.replace(section, "\n" + wrapper.format(section) + "\n", 1),
        encoding="utf-8",
    )
    assert any(
        "root-env" in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("physically inside", "preferably inside"),
        ("is forbidden", "is optional"),
        ("per-task `.env.example` approval", "implicit `.env.example` approval"),
    ],
)
def test_tracked_worktree_obligation_cannot_weaken(
    tmp_path: Path, old: str, new: str
) -> None:
    _guardrail_fixture_tree(tmp_path)
    for name in ("AGENTS.md", ".junie/guidelines.md"):
        p = tmp_path / name
        text = p.read_text(encoding="utf-8")
        assert old in text
        p.write_text(text.replace(old, new), encoding="utf-8")
    assert any(
        "root-worktree" in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


def test_canonical_check_invokes_semantics_without_sync_or_processes(
    monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    contract = mirror.load_contract()
    contract["guardrail_obligations"][0]["required"] = [
        "intentionally missing contract clause"
    ]

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("read-only checker attempted mutation or process execution")

    monkeypatch.setattr(mirror, "do_sync", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(shutil, "copy2", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    assert mirror.do_check(contract) == 1
    assert "[guardrail_semantics] root-env" in capsys.readouterr().err


def test_parity_output_separates_native_execution(capsys: Any) -> None:
    assert mirror.do_check(mirror.load_contract()) == 0
    output = capsys.readouterr().out
    assert "Junie mirror parity OK" in output
    assert "Guardrail semantic contract OK" in output
    assert "Native loading/execution: NOT_PROVEN by this check" in output


@pytest.mark.parametrize("indent", [0, 1, 3])
@pytest.mark.parametrize("closing_length", [3, 5])
def test_indented_fenced_rules_cannot_satisfy_guardrail(
    tmp_path: Path, indent: int, closing_length: int
) -> None:
    _guardrail_fixture_tree(tmp_path)
    path = tmp_path / "AGENTS.md"
    text = path.read_text(encoding="utf-8")
    section = guardrail_section(text, "Env File Guardrail")
    assert section is not None
    prefix = " " * indent
    example = f"\n{prefix}```markdown\n{section}\n{prefix}{'`' * closing_length}\n"
    path.write_text(text.replace(section, example, 1), encoding="utf-8")
    assert any(
        "root-env" in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


@pytest.mark.parametrize("prefix", ["    ", "        ", "\t", " \t"])
def test_indented_code_rules_cannot_satisfy_guardrail(
    tmp_path: Path, prefix: str
) -> None:
    _guardrail_fixture_tree(tmp_path)
    path = tmp_path / "AGENTS.md"
    text = path.read_text(encoding="utf-8")
    section = guardrail_section(text, "Env File Guardrail")
    assert section is not None
    example = "\n" + "\n".join(prefix + line for line in section.splitlines()) + "\n"
    path.write_text(text.replace(section, example, 1), encoding="utf-8")
    assert any(
        "root-env" in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


@pytest.mark.parametrize("indent", [0, 3])
def test_supported_prose_indentation_keeps_guardrail_authority(
    tmp_path: Path, indent: int
) -> None:
    _guardrail_fixture_tree(tmp_path)
    path = tmp_path / "AGENTS.md"
    text = path.read_text(encoding="utf-8")
    section = guardrail_section(text, "Env File Guardrail")
    assert section is not None
    prose = (
        "\n"
        + "\n".join(" " * indent + line.lstrip() for line in section.splitlines())
        + "\n"
    )
    path.write_text(text.replace(section, prose, 1), encoding="utf-8")
    assert check_obligations(tmp_path, OBLIGATIONS) == []


@pytest.mark.parametrize("indent", [0, 3])
def test_lazy_quote_continuations_cannot_satisfy_guardrail(
    tmp_path: Path, indent: int
) -> None:
    _guardrail_fixture_tree(tmp_path)
    path = tmp_path / "AGENTS.md"
    text = path.read_text(encoding="utf-8")
    section = guardrail_section(text, "Env File Guardrail")
    assert section is not None
    item = next(item for item in OBLIGATIONS if item["id"] == "root-env")
    example = (
        "\n" + " " * indent + "> Example only:\n" + " ".join(item["required"]) + "\n"
    )
    path.write_text(text.replace(section, example, 1), encoding="utf-8")
    assert any(
        "root-env" in issue for issue in check_obligations(tmp_path, OBLIGATIONS)
    )


def test_blank_line_restores_prose_authority_after_quote(tmp_path: Path) -> None:
    _guardrail_fixture_tree(tmp_path)
    path = tmp_path / "AGENTS.md"
    text = path.read_text(encoding="utf-8")
    section = guardrail_section(text, "Env File Guardrail")
    assert section is not None
    path.write_text(
        text.replace(section, "\n> Example only\n\n" + section, 1), encoding="utf-8"
    )
    assert check_obligations(tmp_path, OBLIGATIONS) == []
