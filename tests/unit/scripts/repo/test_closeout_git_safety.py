"""Real Git regressions for the offline closeout verifier's callback boundary."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import sys

import pytest

from memory import proof
from scripts.engineering.repo import closeout_runtime, closeout_state
from tests.helpers.isolated_git import init_tracked_fixture_repo, run_isolated_git

pytestmark = pytest.mark.unit


@pytest.fixture
def git_case(tmp_path: Path):
    root = init_tracked_fixture_repo(tmp_path / "repo")
    (root / ".git/info").mkdir(exist_ok=True)
    marker = tmp_path / "callback-ran.txt"
    callback = tmp_path / "callback.py"
    callback.write_text(
        "from pathlib import Path\nimport sys\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
        "if len(sys.argv) > 1 and sys.argv[1] == 'textconv':\n"
        "    sys.stdout.buffer.write(Path(sys.argv[-1]).read_bytes())\n"
        "elif len(sys.argv) > 1 and sys.argv[1] == 'clean':\n"
        "    sys.stdout.buffer.write(sys.stdin.buffer.read())\n",
        encoding="utf-8",
    )
    command = " ".join(
        shlex.quote(Path(value).as_posix()) for value in (sys.executable, str(callback))
    )

    def git(*args: str) -> str:
        result = run_isolated_git(root, *args)
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    return root, marker, command, git


def _dirty(root: Path) -> tuple[str, bool]:
    (root / "tracked.py").write_text("VALUE = 200\n", encoding="utf-8")
    return proof._task_diff_state(root, proof.load_policy(), [], timeout=10)


def test_configured_fsmonitor_is_never_executed(git_case) -> None:
    root, marker, command, git = git_case
    git("config", "core.fsmonitor", command)
    assert _dirty(root)[1] is True
    assert not marker.exists()


def test_configured_textconv_is_never_executed(git_case) -> None:
    root, marker, command, git = git_case
    (root / ".git/info/attributes").write_text("tracked.py diff=probe\n")
    git("config", "diff.probe.textconv", command + " textconv")
    assert _dirty(root)[1] is True
    assert not marker.exists()


@pytest.mark.parametrize("driver", ["probe", "set", "unset", "unspecified"])
def test_active_clean_filter_is_rejected_before_execution(
    git_case, driver: str
) -> None:
    root, marker, command, git = git_case
    (root / ".git/info/attributes").write_text(f"tracked.py filter={driver}\n")
    git("config", f"filter.{driver}.clean", command + " clean")
    with pytest.raises(proof.ProofError, match="filter"):
        _dirty(root)
    assert not marker.exists()


def test_unused_filter_configuration_does_not_block_verification(git_case) -> None:
    root, marker, command, git = git_case
    git("config", "filter.unused.clean", command + " clean")
    assert _dirty(root)[1] is True
    assert not marker.exists()


@pytest.mark.parametrize("setting", ["GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"])
def test_parent_bookends_ignore_inherited_filter_configuration(
    git_case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setting: str
) -> None:
    root, marker, command, git = git_case
    registry = root / "configs/quality/agent_guard_budget_surfaces.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "owner": "fixture",
                "surfaces": [
                    {"pattern": "configs/quality/*budget*.json", "kind": "budget"}
                ],
            }
        ),
        encoding="utf-8",
    )
    git("add", ".")
    git("commit", "--no-gpg-sign", "--no-verify", "-qm", "fixture policy")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    config = tmp_path / "ambient.gitconfig"
    git(
        "config",
        "--file",
        str(config),
        "filter.ambient-probe.clean",
        command + " clean",
    )
    (root / ".git/info/attributes").write_text("tracked.py filter=ambient-probe\n")
    (root / "tracked.py").write_text("VALUE = 20\n", encoding="utf-8")
    monkeypatch.delenv("GIT_CONFIG_NOSYSTEM", raising=False)
    monkeypatch.setenv(setting, str(config))
    closeout_state.capture(root, closeout_runtime._environment())
    assert not marker.exists()


def test_replace_refs_cannot_change_measured_git_objects(git_case) -> None:
    root, _marker, _command, git = git_case
    original = git("rev-parse", "HEAD")
    (root / "tracked.py").write_text("VALUE = 2\n", encoding="utf-8")
    git("add", "tracked.py")
    git("commit", "--no-gpg-sign", "--no-verify", "-qm", "replacement fixture")
    replacement = git("rev-parse", "HEAD")
    git("replace", original, replacement)
    assert proof._git(root, "show", original + ":tracked.py").splitlines() == [
        b"VALUE = 1"
    ]


def test_index_only_change_invalidates_the_canonical_diff_identity(git_case) -> None:
    root, _marker, _command, git = git_case
    original = (root / "tracked.py").read_bytes()
    before = proof._task_diff_state(root, proof.load_policy(), [], timeout=10)
    (root / "tracked.py").write_text("VALUE = 3\n", encoding="utf-8")
    git("add", "tracked.py")
    (root / "tracked.py").write_bytes(original)
    after = proof._task_diff_state(root, proof.load_policy(), [], timeout=10)
    assert after[0] != before[0]
    assert after[1] is True
