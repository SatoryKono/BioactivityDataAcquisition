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
    with pytest.raises(SystemExit, match="invalid git revision"):
        module.find_collapsing_commits("--upload-pack=evil", "HEAD", repo=repo)
    with pytest.raises(SystemExit, match="invalid git revision"):
        module.find_collapsing_commits("HEAD", "-c", repo=repo)
    with pytest.raises(SystemExit, match="invalid git repository path"):
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
    with pytest.raises(SystemExit):
        module.find_collapsing_commits("missing-trusted-base", "HEAD", repo=repo)
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "src/new.txt").write_text("new")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "candidate")
    tip = _git(repo, "rev-parse", "HEAD").strip()
    (repo / ".git/shallow").write_text(tip + "\n")
    with pytest.raises(SystemExit):
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
        SystemExit, match="Git evidence unavailable or timed out"
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
    with pytest.raises(SystemExit):
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
    checkout = next(
        s for s in steps if s.get("uses", "").startswith("actions/checkout@")
    )
    assert (
        checkout["with"]["ref"]
        == "${{ github.event.pull_request.base.sha || 'refs/heads/main' }}"
    )
    assert checkout["with"]["persist-credentials"] is False
    assert checkout["with"]["fetch-depth"] == 0
    assert len([s for s in steps if "uses" in s]) == 1
    status = steps[-1]
    assert "always()" in status["if"]
    assert "context=bioetl/no-partial-tree" in status["run"]
    assert status["env"]["TIP_SHA"] == "${{ steps.range.outputs.tip }}"
    assert "job.status == 'success'" in status["env"]["RESULT_STATE"]


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
    with pytest.raises(SystemExit, match="unmerged index"):
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
    with pytest.raises(SystemExit, match="unavailable or invalid"):
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
    with pytest.raises(SystemExit, match="unavailable or invalid"):
        module._load_event_range("push", link)


def test_event_reader_accepts_in_directory_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "event.json"
    path.write_text('{"before":"' + "1" * 40 + '","after":"' + "2" * 40 + '"}')
    assert module._load_event_range("push", path) == ("1" * 40, "2" * 40)
