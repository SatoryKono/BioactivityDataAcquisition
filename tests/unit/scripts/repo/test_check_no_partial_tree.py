# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for the partial-tree commit guard (#11709)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.repo import check_no_partial_tree as module
from tests.helpers.isolated_git import run_isolated_git


pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> str:
    result = run_isolated_git(repo, *args)
    result.check_returncode()
    return result.stdout


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "test")
    _git(tmp_path, "config", "user.email", "test@local")
    for name in (
        "src",
        "docs",
        "scripts",
        "configs",
        "reports",
        "tests",
        "grafana",
        "data",
        ".github",
        "contracts",
    ):
        (tmp_path / name).mkdir()
        (tmp_path / name / "keep.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("license", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "full tree")
    return tmp_path


def _commit_partial_tree(repo: Path, message: str) -> str:
    _git(repo, "read-tree", "--empty")
    _git(repo, "add", "reports")
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def test_collapsed_tree_rule_accepts_full_restructure_and_rejects_subset() -> None:
    base = frozenset(
        {
            "src",
            "docs",
            "reports",
            "README.md",
            "configs",
            "scripts",
            "tests",
            "grafana",
            "data",
            ".github",
            "LICENSE",
        }
    )
    assert module.is_collapsed_tree(base, base) is False
    assert module.is_collapsed_tree(base, base | {"new_area"}) is False
    assert module.is_collapsed_tree(base, (base - {"src"}) | {"renamed_src"}) is False
    assert module.is_collapsed_tree(base, frozenset({"reports"})) is True
    assert module.is_collapsed_tree(base, frozenset()) is True
    assert module.is_collapsed_tree(frozenset({"a"}), frozenset({"a"})) is False


def test_guard_flags_partial_tree_commit_in_range(repo: Path) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    bad = _commit_partial_tree(repo, "reports-only snapshot")
    assert module.find_collapsing_commits(healthy, bad, repo=repo) == [bad]


def test_rejects_flag_injection_in_revision_tokens(repo: Path) -> None:
    with pytest.raises(module.EvidenceError, match="invalid git revision"):
        module.find_collapsing_commits("--upload-pack=evil", "HEAD", repo=repo)
    with pytest.raises(module.EvidenceError, match="invalid git revision"):
        module.find_collapsing_commits("HEAD", "-c", repo=repo)
    with pytest.raises(module.EvidenceError, match="invalid git repository path"):
        module.validate_repo("-C")


def test_resolve_revision_uses_end_of_options(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []
    real = module._run_git

    def wrapped(cwd: Path, verb: str, *args: str) -> str:
        seen.append([verb, *args])
        return real(cwd, verb, *args)

    monkeypatch.setattr(module, "_run_git", wrapped)
    sha = module.resolve_revision(repo, "HEAD")
    assert module._SHA_RE.fullmatch(sha)
    assert any(row[0] == "rev-parse" and "--end-of-options" in row for row in seen)


def test_branch_before_a_new_main_anchor_is_not_retroactively_partial(
    repo: Path,
) -> None:
    old = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "-qb", "feature-before-anchor")
    (repo / "src/feature.txt").write_text("ordinary feature")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "feature before new runtime")
    _git(repo, "checkout", "--detach", old)
    (repo / ".devin").mkdir()
    (repo / ".devin/keep.md").write_text("new required runtime anchor")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "add runtime on main")
    trusted = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "feature-before-anchor")
    before = (repo / ".git/index").read_bytes()
    assert module.check_index_tree(repo, trusted) == []
    assert (repo / ".git/index").read_bytes() == before
    assert module.find_collapsing_commits(trusted, "HEAD", repo=repo) == []
    _git(repo, "merge", "--no-edit", trusted)
    assert module.find_collapsing_commits(trusted, "HEAD", repo=repo) == []
    _git(repo, "rm", "-qr", ".devin")
    _git(repo, "commit", "-qm", "remove inherited runtime")
    bad = _git(repo, "rev-parse", "HEAD").strip()
    assert module.find_collapsing_commits(trusted, "HEAD", repo=repo) == [bad]


def test_unrelated_reports_only_root_cannot_hide_in_a_merge(repo: Path) -> None:
    trusted = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "--orphan", "unrelated-report-snapshot")
    _git(repo, "read-tree", "--empty")
    _git(repo, "add", "reports")
    _git(repo, "commit", "-qm", "unrelated reports-only root")
    # The synthetic orphan leaves untracked copies of the original fixture files.
    _git(repo, "checkout", "--force", "--detach", trusted)
    _git(
        repo,
        "merge",
        "--allow-unrelated-histories",
        "--no-edit",
        "unrelated-report-snapshot",
    )
    with pytest.raises(module.EvidenceError, match="unrelated root"):
        module.find_collapsing_commits(trusted, "HEAD", repo=repo)


def test_guard_passes_clean_range(repo: Path) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "src" / "feature.txt").write_text("feature", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "feature")
    tip = _git(repo, "rev-parse", "HEAD").strip()
    assert module.find_collapsing_commits(healthy, tip, repo=repo) == []


def test_more_than_three_roots_and_dummy_addition_do_not_hide_collapse(
    repo: Path,
) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "read-tree", "--empty")
    for name in ("reports", "docs", "configs", "scripts"):
        _git(repo, "add", name)
    (repo / "dummy.txt").write_text("dummy")
    _git(repo, "add", "dummy.txt")
    _git(repo, "commit", "-qm", "partial with dummy")
    bad = _git(repo, "rev-parse", "HEAD").strip()
    assert module.find_collapsing_commits(healthy, bad, repo=repo) == [bad]
    _git(repo, "read-tree", healthy)
    _git(repo, "commit", "-qm", "restore full tree")
    assert module.find_collapsing_commits(healthy, "HEAD", repo=repo) == [bad]


def test_directory_relocation_and_optional_root_file_removal_are_valid(
    repo: Path,
) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "mv", "src", "renamed_src")
    _git(repo, "rm", "README.md")
    _git(repo, "rm", "-r", "data")
    _git(repo, "commit", "-qm", "legitimate move")
    assert module.find_collapsing_commits(healthy, "HEAD", repo=repo) == []


def test_merge_commit_cannot_hide_an_intermediate_collapse(repo: Path) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    bad = _commit_partial_tree(repo, "partial")
    tree = _git(repo, "rev-parse", healthy + "^{tree}").strip()
    merged = _git(
        repo, "commit-tree", tree, "-p", bad, "-p", healthy, "-m", "full merge"
    ).strip()
    assert module.find_collapsing_commits(healthy, merged, repo=repo) == [bad]


def test_sparse_configuration_and_skip_worktree_are_separate_from_tree(
    repo: Path,
) -> None:
    assert module.check_checkout_state(repo) == []
    _git(repo, "config", "core.sparseCheckout", "true")
    assert "sparse checkout is enabled" in module.check_checkout_state(repo)
    _git(repo, "config", "core.sparseCheckout", "false")
    _git(repo, "update-index", "--skip-worktree", "src/keep.txt")
    assert "skip-worktree entries exist in index" in module.check_checkout_state(repo)
    assert module.main(["--repo", str(repo), "--base", "HEAD"]) == 2


def test_shallow_and_missing_base_never_pass(repo: Path) -> None:
    with pytest.raises(module.EvidenceError):
        module.find_collapsing_commits("missing-trusted-base", "HEAD", repo=repo)
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "src/new.txt").write_text("new")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "candidate")
    tip = _git(repo, "rev-parse", "HEAD").strip()
    (repo / ".git/shallow").write_text(tip + "\n")
    with pytest.raises(module.EvidenceError):
        module.find_collapsing_commits(base, tip, repo=repo)


def test_shallow_boundary_at_trusted_base_keeps_complete_range_qualified(
    repo: Path,
) -> None:
    """History older than the trusted base need not be downloaded again."""
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "src/new.txt").write_text("new")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "candidate")
    (repo / ".git/shallow").write_text(base + "\n")
    assert module.find_collapsing_commits(base, "HEAD", repo=repo) == []


def test_git_timeout_is_explicit_and_does_not_echo_exception(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    def timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("private-value", 10)

    monkeypatch.setattr(module.subprocess, "run", timeout)
    with pytest.raises(
        module.EvidenceError, match="Git evidence unavailable or timed out"
    ) as caught:
        module.resolve_revision(repo, "HEAD")
    assert "private-value" not in str(caught.value)


@pytest.mark.parametrize("event_name", ["pull_request", "pull_request_target"])
def test_pr_range_uses_head_and_base_instead_of_merge_sha(event_name: str) -> None:
    base, head = "a" * 40, "b" * 40
    event = {
        "pull_request": {"base": {"sha": base}, "head": {"sha": head}},
        "before": "c" * 40,
        "after": "d" * 40,
    }
    assert module.select_event_range(event_name, event) == (base, head)


def test_push_and_manual_have_separate_range_contracts() -> None:
    base, tip = "a" * 40, "b" * 40
    assert module.select_event_range("push", {"before": base, "after": tip}) == (
        base,
        tip,
    )
    assert module.select_event_range(
        "workflow_dispatch", {"inputs": {"base": "origin/main", "tip": "HEAD"}}
    ) == ("origin/main", "HEAD")


@pytest.mark.parametrize(
    "event_name,event",
    [
        ("push", {"before": "0" * 40, "after": "a" * 40}),
        ("push", {"before": "a" * 40, "after": "0" * 40}),
        ("pull_request", {"pull_request": {"head": {"sha": "b" * 40}}}),
        ("workflow_dispatch", {"inputs": {"base": "", "tip": "HEAD"}}),
        ("workflow_dispatch", {"inputs": {"base": None, "tip": "HEAD"}}),
        ("workflow_dispatch", {"inputs": {"base": "--help", "tip": "HEAD"}}),
        ("unknown", {}),
    ],
)
def test_unqualified_event_identity_is_never_a_default_pass(
    event_name: str, event: dict
) -> None:
    with pytest.raises(module.EvidenceError):
        module.select_event_range(event_name, event)


def test_proposed_index_is_checked_without_writing_objects_or_index(repo: Path) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    assert module.check_index_tree(repo, healthy) == []
    _git(repo, "read-tree", "--empty")
    _git(repo, "add", "reports", "docs", "configs", "scripts")
    before = (repo / ".git/index").read_bytes()
    assert module.check_index_tree(repo, healthy) == [
        "proposed index loses directory anchors"
    ]
    assert (repo / ".git/index").read_bytes() == before
    assert module.main(["--repo", str(repo), "--base", healthy, "--check-index"]) == 2


def test_root_file_cannot_impersonate_a_directory_anchor(repo: Path) -> None:
    healthy = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "rm", "-qr", "src")
    (repo / "src").write_text("dummy anchor")
    _git(repo, "add", "src")
    before = (repo / ".git/index").read_bytes()
    assert module.check_index_tree(repo, healthy) == [
        "proposed index loses directory anchors"
    ]
    assert (repo / ".git/index").read_bytes() == before
    assert module.main(["--repo", str(repo), "--base", healthy, "--check-index"]) == 2
    _git(repo, "commit", "-qm", "replace directory with root file")
    bad = _git(repo, "rev-parse", "HEAD").strip()
    assert module.find_collapsing_commits(healthy, bad, repo=repo) == [bad]


@pytest.mark.parametrize("filename", ["new.py", "keep.txt"])
def test_intent_to_add_cannot_preserve_a_future_commit_anchor(
    repo: Path, filename: str
) -> None:
    trusted = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "rm", "-qr", "src")
    (repo / "src").mkdir()
    (repo / "src" / filename).write_text("")
    _git(repo, "add", "-N", "src")
    before = (repo / ".git/index").read_bytes()
    with pytest.raises(module.EvidenceError, match="intent-to-add"):
        module.check_index_tree(repo, trusted)
    assert (repo / ".git/index").read_bytes() == before
    assert module.main(["--repo", str(repo), "--base", trusted, "--check-index"]) == 2
    _git(repo, "add", "src")
    assert module.check_index_tree(repo, trusted) == []


def test_index_replacement_during_inspection_is_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = module._run_git
    reads = 0

    def replacement(path: Path, verb: str, *args: str) -> str:
        nonlocal reads
        result = original(path, verb, *args)
        if verb == "ls-files":
            reads += 1
            if reads == 2:
                return result + "100644 " + "a" * 40 + " 0\tconcurrent.txt\x00"
        return result

    monkeypatch.setattr(module, "_run_git", replacement)
    assert module.check_index_tree(repo, "HEAD") == ["index changed during inspection"]


def test_guard_workflow_runs_trusted_base_code_and_publishes_candidate_status() -> None:
    import yaml

    root = Path(__file__).resolve().parents[4]
    workflow = yaml.safe_load(
        (root / ".github/workflows/no-partial-tree-commits.yml").read_text()
    )
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"pull_request_target", "push", "workflow_dispatch"}
    assert triggers["pull_request_target"]["branches"] == ["main"]
    assert triggers["workflow_dispatch"]["inputs"]["base"]["required"] is True
    job = workflow["jobs"]["no-partial-tree"]
    assert job["permissions"] == {"contents": "read", "statuses": "write"}
    steps = job["steps"]
    checkout = steps[0]["run"]
    assert (
        "git remote add origin https://github.com/SatoryKono/BioactivityDataAcquisition.git"
        in checkout
    )
    assert "fetch --no-tags origin refs/heads/main" in checkout
    assert "checkout --detach FETCH_HEAD" in checkout
    assert "init.templateDir=" in checkout
    assert "core.hooksPath=/dev/null" in checkout
    assert "${{" not in checkout
    assert "GH_TOKEN" not in steps[0].get("env", {})
    assert not any("uses" in s for s in steps)
    status = steps[-1]
    assert "always()" in status["if"]
    assert "context=bioetl/no-partial-tree" in status["run"]
    assert status["env"]["TIP_SHA"] == "${{ steps.range.outputs.tip }}"
    assert "job.status == 'success'" in status["env"]["RESULT_STATE"]


@pytest.mark.parametrize("tip_form", ["sha", "branch", "tracking", "missing"])
def test_ci_bootstrap_checks_out_main_without_candidate_files(
    repo: Path, tip_form: str
) -> None:
    """Execute the workflow bootstrap against a synthetic local origin, no network."""
    import shlex
    import os
    import subprocess
    import sys
    import yaml

    root = Path(__file__).resolve().parents[4]
    guard = repo / "scripts/engineering/repo/check_no_partial_tree.py"
    guard.parent.mkdir(parents=True)
    guard.write_bytes(
        (root / "scripts/engineering/repo/check_no_partial_tree.py").read_bytes()
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "trusted checker fixture")
    trusted = _git(repo, "rev-parse", "HEAD").strip()
    if _git(repo, "branch", "--show-current").strip() != "main":
        _git(repo, "branch", "main", trusted)
    _git(repo, "checkout", "-qb", "untrusted-candidate")
    (repo / "src/untrusted.py").write_text("raise RuntimeError('candidate executed')")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "candidate must remain data")
    candidate = _git(repo, "rev-parse", "HEAD").strip()
    workflow = yaml.safe_load(
        (root / ".github/workflows/no-partial-tree-commits.yml").read_text()
    )
    script = workflow["jobs"]["no-partial-tree"]["steps"][0]["run"]
    checkout = repo.with_name(repo.name + "-ci")
    checkout.mkdir()
    for line in script.splitlines():
        argv = shlex.split(line)
        if argv[0] == "timeout":
            argv = argv[2:]
        assert argv[0] == "git"
        argv = [
            repo.as_uri()
            if value == "https://github.com/SatoryKono/BioactivityDataAcquisition.git"
            else value
            for value in argv
        ]
        _git(checkout, *argv[1:])
    assert _git(checkout, "rev-parse", "HEAD").strip() == trusted
    fetch_step = next(
        row
        for row in workflow["jobs"]["no-partial-tree"]["steps"]
        if row.get("id") == "objects"
    )
    program = fetch_step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    tip = {
        "sha": candidate,
        "branch": "untrusted-candidate",
        "tracking": "origin/untrusted-candidate",
        "missing": "branch-that-does-not-exist",
    }[tip_form]
    output = checkout / "outputs.txt"
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", program],
        cwd=checkout,
        env=dict(os.environ, BASE_REF=trusted, TIP_REF=tip, GITHUB_OUTPUT=str(output)),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if tip_form == "missing":
        assert result.returncode != 0
        assert not output.exists()
        assert _git(checkout, "rev-parse", "HEAD").strip() == trusted
        assert not (checkout / "src/untrusted.py").exists()
        return
    assert result.returncode == 0, result.stderr
    assert dict(line.split("=", 1) for line in output.read_text().splitlines()) == {
        "base": trusted,
        "tip": candidate,
    }
    assert _git(checkout, "rev-parse", "HEAD").strip() == trusted
    assert not (checkout / "src/untrusted.py").exists()


def test_real_sparse_index_directory_entries_are_detected(repo: Path) -> None:
    _git(repo, "sparse-checkout", "init", "--cone", "--sparse-index")
    _git(repo, "sparse-checkout", "set", "reports")
    problems = module.check_checkout_state(repo)
    assert "sparse checkout is enabled" in problems
    assert "sparse directory entries exist in index" in problems


def test_unmerged_index_is_not_a_proposed_complete_tree(repo: Path) -> None:
    import subprocess

    healthy = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "-qb", "side")
    (repo / "src/keep.txt").write_text("side")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "side")
    _git(repo, "checkout", "-qb", "other", healthy)
    (repo / "src/keep.txt").write_text("other")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "other")
    with pytest.raises(subprocess.CalledProcessError):
        _git(repo, "merge", "side")
    with pytest.raises(module.EvidenceError, match="unmerged index"):
        module.check_index_tree(repo, healthy)


def test_event_cli_errors_do_not_echo_payload(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    path = repo / "invalid-event.json"
    path.write_text("private-payload-not-for-logs")
    assert (
        module.main(
            ["--repo", str(repo), "--event-name", "push", "--event-json", str(path)]
        )
        == 2
    )
    output = capsys.readouterr().out
    assert "ERROR" in output
    assert "private-payload" not in output


def test_sparse_index_setting_is_reported_before_directory_collapse(repo: Path) -> None:
    _git(repo, "config", "index.sparse", "true")
    assert "sparse index is enabled" in module.check_checkout_state(repo)


@pytest.mark.parametrize("relative", [False, True])
def test_event_reader_refuses_outside_and_prefix_sibling_paths(
    tmp_path, monkeypatch, relative
):
    """A sibling sharing the directory prefix is outside the invocation boundary."""
    inside = tmp_path / "checkout"
    outside = tmp_path / "checkout-private"
    inside.mkdir()
    outside.mkdir()
    event = outside / "event.json"
    event.write_text('{"before":"' + "1" * 40 + '","after":"' + "2" * 40 + '"}')
    monkeypatch.chdir(inside)
    candidate = Path("../checkout-private/event.json") if relative else event
    with pytest.raises(module.EvidenceError, match="unavailable or invalid"):
        module._load_event_range("push", candidate)


def test_event_reader_resolves_symlink_before_boundary_check(tmp_path, monkeypatch):
    inside = tmp_path / "checkout"
    inside.mkdir()
    outside = tmp_path / "private.json"
    outside.write_text("{}")
    link = inside / "event.json"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("host does not allow fixture symlinks")
    monkeypatch.chdir(inside)
    with pytest.raises(module.EvidenceError, match="unavailable or invalid"):
        module._load_event_range("push", link)


def test_event_reader_accepts_in_directory_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "event.json"
    path.write_text('{"before":"' + "1" * 40 + '","after":"' + "2" * 40 + '"}')
    assert module._load_event_range("push", path) == ("1" * 40, "2" * 40)


def test_alternate_index_cannot_hide_real_skip_worktree_flags(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Qualify the actual repository index, ignoring an ambient clean alternate."""
    alternate = repo / "alternate-index"
    alternate.write_bytes((repo / ".git/index").read_bytes())
    _git(repo, "update-index", "--skip-worktree", "src/keep.txt")
    real_before = (repo / ".git/index").read_bytes()
    monkeypatch.setenv("GIT_INDEX_FILE", str(alternate))

    assert "skip-worktree entries exist in index" in module.check_checkout_state(repo)
    assert (repo / ".git/index").read_bytes() == real_before


def test_unrelated_system_exit_is_not_converted_to_evidence_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve a caller's requested termination instead of masking it as bad Git."""

    def stop(*args: object, **kwargs: object) -> int:
        raise SystemExit(130)

    monkeypatch.setattr(module, "_run_checks", stop)
    with pytest.raises(SystemExit) as caught:
        module.main([])
    assert caught.value.code == 130


def test_ambient_config_cannot_hide_real_sparse_checkout(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A command-scoped override must not replace the repository's sparse setting."""
    _git(repo, "config", "core.sparseCheckout", "true")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.sparseCheckout")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "false")
    assert "sparse checkout is enabled" in module.check_checkout_state(repo)


def test_supplied_commit_index_cannot_hide_missing_directory(repo, monkeypatch):
    trusted = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "rm", "-qr", "src")
    supplied = repo / "commit-index"
    supplied.write_bytes((repo / ".git/index").read_bytes())
    _git(repo, "read-tree", "HEAD")
    default_before = (repo / ".git/index").read_bytes()
    supplied_before = supplied.read_bytes()
    monkeypatch.setenv("GIT_INDEX_FILE", str(supplied))
    assert module.check_index_tree(repo, trusted) == [
        "proposed index loses directory anchors"
    ]
    assert (repo / ".git/index").read_bytes() == default_before
    assert supplied.read_bytes() == supplied_before


def test_supplied_index_skip_flags_are_checked_as_well_as_default(repo, monkeypatch):
    _git(repo, "update-index", "--skip-worktree", "src/keep.txt")
    supplied = repo / "commit-index"
    supplied.write_bytes((repo / ".git/index").read_bytes())
    _git(repo, "update-index", "--no-skip-worktree", "src/keep.txt")
    monkeypatch.setenv("GIT_INDEX_FILE", str(supplied))
    assert "skip-worktree entries exist in index" in module.check_checkout_state(repo)


def test_full_supplied_commit_index_remains_valid_and_readonly(repo, monkeypatch):
    trusted = _git(repo, "rev-parse", "HEAD").strip()
    supplied = repo / "commit-index"
    supplied.write_bytes((repo / ".git/index").read_bytes())
    before = supplied.read_bytes()
    monkeypatch.setenv("GIT_INDEX_FILE", str(supplied))
    assert module.check_checkout_state(repo) == []
    assert module.check_index_tree(repo, trusted) == []
    assert supplied.read_bytes() == before
    assert (repo / ".git/index").read_bytes() == before


def test_empty_supplied_index_is_unqualified(repo, monkeypatch):
    monkeypatch.setenv("GIT_INDEX_FILE", "")
    with pytest.raises(module.EvidenceError, match="empty supplied index"):
        module.check_index_tree(repo, "HEAD")
