"""Unit tests for the local ci presubmit gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.engineering.ci import presubmit_gate as gate
from scripts.engineering.ci.pr_gate import CatalogError

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

_REPO = Path(__file__).resolve().parents[6]
_CATALOG = _REPO / "configs/quality/github_required_checks.yaml"
_BASE = "a" * 40
_HEAD = "b" * 40


def _argv() -> list[str]:
    return ["--base", "origin/main", "--head", "HEAD", "--catalog", str(_CATALOG)]


def _install_stages(
    monkeypatch: pytest.MonkeyPatch,
    changed: list[str],
    *,
    order: list[str] | None = None,
    ruff: bool = True,
    mypy: bool = True,
    affected: bool = True,
    architecture: bool = True,
) -> None:
    def resolve(ref: str, *, repo: Path | None = None) -> str:
        del ref, repo
        return _HEAD

    def collect(**kwargs: object) -> list[str]:
        del kwargs
        if order is not None:
            order.append("diff")
        return list(changed)

    def run_ruff() -> bool:
        if order is not None:
            order.append("ruff")
        return ruff

    def run_mypy() -> bool:
        if order is not None:
            order.append("mypy")
        return mypy

    def run_affected(base_sha: str, head_sha: str, files: list[str]) -> bool:
        del base_sha, head_sha, files
        if order is not None:
            order.append("tests")
        return affected

    def run_architecture() -> bool:
        if order is not None:
            order.append("arch")
        return architecture

    monkeypatch.setattr(gate, "resolve_ref", resolve)
    monkeypatch.setattr(gate, "collect_changed_files", collect)
    monkeypatch.setattr(gate, "run_ruff", run_ruff)
    monkeypatch.setattr(gate, "run_mypy", run_mypy)
    monkeypatch.setattr(gate, "run_affected_tests", run_affected)
    monkeypatch.setattr(gate, "run_fast_architecture", run_architecture)


def test_stage_order_for_python_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Python diffs run ruff, strict mypy, classify, affected tests, then architecture."""
    order: list[str] = []
    real_classify = gate.classify_changes

    def classify(catalog: object, changed: list[str], *, head_sha: str) -> object:
        order.append("classify")
        return real_classify(catalog, changed, head_sha=head_sha)

    _install_stages(monkeypatch, ["src/bioetl/domain/sample.py"], order=order)
    monkeypatch.setattr(gate, "classify_changes", classify)

    assert gate.main(_argv()) == 0
    assert order == ["diff", "ruff", "mypy", "classify", "tests", "arch"]


def test_ruff_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing ruff stage exits 1 even when later stages pass."""
    _install_stages(
        monkeypatch,
        ["scripts/engineering/ci/presubmit_gate.py"],
        ruff=False,
    )
    assert gate.main(_argv()) == 1


def test_mypy_failure_propagates_for_each_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Type errors under src/bioetl and src/memory both reach strict mypy."""
    for changed in (
        ["src/bioetl/domain/sample.py"],
        ["src/memory/store.py"],
    ):
        _install_stages(monkeypatch, changed, mypy=False)
        assert gate.main(_argv()) == 1


def test_non_python_diff_skips_mypy(monkeypatch: pytest.MonkeyPatch) -> None:
    """A classified docs diff still runs ruff and does not run strict mypy."""
    order: list[str] = []
    _install_stages(
        monkeypatch, ["docs/03-guides/github-local-workflow.md"], order=order
    )
    assert gate.main(_argv()) == 0
    assert order == ["diff", "ruff"]


def test_unknown_path_empty_selection_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unclassified path must not succeed when test selection is empty."""
    _install_stages(monkeypatch, ["vendor/blob.bin"], affected=False)
    assert gate.main(_argv()) == 1


def test_empty_diff_still_runs_fail_closed_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty diff does not return success before Ruff and classification."""
    order: list[str] = []
    seen: dict[str, object] = {}
    real_classify = gate.classify_changes

    def collect(**kwargs: object) -> list[str]:
        seen.update(kwargs)
        order.append("diff")
        return []

    def classify(catalog: object, changed: list[str], *, head_sha: str) -> object:
        order.append("classify")
        matrix = real_classify(catalog, changed, head_sha=head_sha)
        assert matrix["decisions"]["tests"]["decision"] == "required"
        assert matrix["decisions"]["lint-arch"]["decision"] == "required"
        return matrix

    _install_stages(monkeypatch, [], order=order)
    monkeypatch.setattr(gate, "collect_changed_files", collect)
    monkeypatch.setattr(gate, "classify_changes", classify)

    assert gate.main(_argv()) == 0
    assert order == ["diff", "ruff", "classify", "tests", "arch"]
    assert seen["event_name"] == "pull_request"
    assert seen["base_sha"] == _HEAD
    assert seen["head_sha"] == _HEAD


def test_required_reads_nested_decision() -> None:
    """Gate decisions live under matrix['decisions'], not at the top level."""
    matrix = {
        "decisions": {
            "lint-arch": {"decision": "required"},
            "tests": {"decision": "not_applicable"},
        }
    }
    assert gate._required(matrix, "lint-arch") is True
    assert gate._required(matrix, "tests") is False
    with pytest.raises(CatalogError, match="decisions must be a mapping"):
        gate._required({"tests": "required"}, "tests")


def test_architecture_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """A required lint-arch gate fails the process when architecture pytest fails."""
    _install_stages(
        monkeypatch,
        ["src/bioetl/domain/sample.py"],
        architecture=False,
    )
    assert gate.main(_argv()) == 1


def test_rename_paths_reach_affected_selector() -> None:
    """Rename diffs pass both paths into the canonical selector."""
    command = gate.affected_tests_command(
        _BASE,
        _HEAD,
        ["src/bioetl/old_name.py", "src/bioetl/new_name.py"],
    )
    assert command[command.index("--base-sha") + 1] == _BASE
    assert command[command.index("--head-sha") + 1] == _HEAD
    changed = [
        command[index + 1]
        for index, token in enumerate(command)
        if token == "--changed-file"
    ]
    assert changed == ["src/bioetl/old_name.py", "src/bioetl/new_name.py"]


def test_empty_selection_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Selector success with no targets is not an empty success."""

    def capture(command: list[str]) -> subprocess.CompletedProcess[str]:
        del command
        return subprocess.CompletedProcess([], 0, stdout="\n", stderr="")

    monkeypatch.setattr(gate, "_capture", capture)
    assert gate.run_affected_tests(_BASE, _HEAD, ["vendor/blob.bin"]) is False


def test_selector_nonzero_and_pytest_nonzero_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selector and pytest non-zero codes propagate as a failed stage."""

    def failed_select(command: list[str]) -> subprocess.CompletedProcess[str]:
        del command
        return subprocess.CompletedProcess([], 1, stdout="", stderr="selection failed")

    monkeypatch.setattr(gate, "_capture", failed_select)
    assert gate.run_affected_tests(_BASE, _HEAD, ["src/bioetl/sample.py"]) is False

    def empty_ok(command: list[str]) -> subprocess.CompletedProcess[str]:
        del command
        return subprocess.CompletedProcess(
            [],
            0,
            stdout="tests/unit/sample.py\n",
            stderr="",
        )

    monkeypatch.setattr(gate, "_capture", empty_ok)
    monkeypatch.setattr(gate, "_run", lambda command: 1)
    assert gate.run_affected_tests(_BASE, _HEAD, ["src/bioetl/sample.py"]) is False


def test_invalid_ref_and_diff_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Broken refs and diff failures exit 1 before a successful result."""

    def broken(ref: str, *, repo: Path | None = None) -> str:
        del ref, repo
        raise ValueError("invalid git ref")

    monkeypatch.setattr(gate, "resolve_ref", broken)
    assert gate.main(_argv()) == 1

    monkeypatch.setattr(gate, "resolve_ref", lambda ref, repo=None: _HEAD)
    monkeypatch.setattr(
        gate,
        "collect_changed_files",
        lambda **kwargs: (_ for _ in ()).throw(OSError("diff failed")),
    )
    assert gate.main(_argv()) == 1


def test_resolve_ref_rejects_injection_and_keeps_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flag-like refs fail before git, and only a matched SHA is returned."""

    def refuse_git(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise AssertionError("git must not run for an invalid ref")

    monkeypatch.setattr(
        "scripts.engineering.repo.check_no_partial_tree.subprocess.run",
        refuse_git,
    )
    with pytest.raises(SystemExit, match="invalid git revision"):
        gate.resolve_ref("--upload-pack=evil")
    with pytest.raises(SystemExit, match="invalid git revision"):
        gate.resolve_ref("HEAD;rm -rf")

    def git_failed(repo: Path, ref: str) -> str:
        del repo, ref
        raise SystemExit("git rev-parse failed: fatal: bad object")

    monkeypatch.setattr(gate, "resolve_revision", git_failed)
    with pytest.raises(SystemExit, match="bad object"):
        gate.resolve_ref("HEAD")

    monkeypatch.setattr(gate, "resolve_revision", lambda repo, ref: "DEADBEEF")
    with pytest.raises(ValueError, match="commit SHA"):
        gate.resolve_ref("HEAD")

    monkeypatch.setattr(gate, "resolve_revision", lambda repo, ref: _BASE)
    assert gate.resolve_ref("HEAD") == _BASE


def test_cli_rejects_flag_ref() -> None:
    """The packaged CLI returns 1 for a flag-like ref before running checks."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.ci",
            "presubmit",
            "--base=--upload-pack=evil",
            "--head=HEAD",
        ],
        cwd=_REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert "invalid git revision" in completed.stderr


def test_unsafe_changed_path_is_rejected() -> None:
    """Changed paths that look like options are not appended to argv."""
    with pytest.raises(ValueError, match="unsafe changed path"):
        gate.affected_tests_command(_BASE, _HEAD, ["--evil"])


def test_run_ruff_format_check_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing ruff format --check is a failed stage and uses the CI trees."""
    commands: list[list[str]] = []

    def record(command: list[str]) -> int:
        commands.append(command)
        return 1 if "format" in command else 0

    monkeypatch.setattr(gate, "_run", record)
    assert gate.run_ruff() is False
    assert commands[0][:6] == ["uv", "run", "--frozen", "--no-build", "ruff", "check"]
    assert commands[1][:7] == [
        "uv",
        "run",
        "--frozen",
        "--no-build",
        "ruff",
        "format",
        "--check",
    ]
    assert commands[1][-3:] == ["src", "tests", "scripts"]


def test_ruff_and_mypy_commands_cover_required_trees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ruff covers src/tests/scripts and mypy stays strict and incremental."""
    commands: list[list[str]] = []

    def record(command: list[str]) -> int:
        commands.append(command)
        return 0

    monkeypatch.setattr(gate, "_run", record)
    assert gate.run_ruff() is True
    assert gate.run_mypy() is True
    assert commands[0][-3:] == ["src", "tests", "scripts"]
    assert commands[1][-3:] == ["src", "tests", "scripts"]
    mypy_command = commands[2]
    assert "--strict" in mypy_command
    assert "--incremental" in mypy_command
    assert "--no-incremental" not in mypy_command
    assert mypy_command[-2:] == ["src/bioetl", "src/memory"]
    assert gate.fast_architecture_command()[4:8] == [
        "pytest",
        "tests/architecture",
        "-m",
        "not slow and not benchmark and not memory",
    ]
    monkeypatch.setattr(gate, "_run", lambda command: 1)
    assert gate.run_fast_architecture() is False
