"""Complete path coverage and unavailable/changing evidence cannot qualify."""

from __future__ import annotations

import os
import subprocess

import pytest

from scripts.engineering.repo.hook_receipts import _SourceDiffScanner as scanner

pytestmark = pytest.mark.unit


def test_partition_covers_every_index_path_once_in_bounded_workers():
    paths = tuple(
        sorted(
            [f"tests/unit/group{i % 31}/test_{i}.py".encode() for i in range(14000)]
            + [b"-flag", b"space name", b"line\nname", b":(exclude)*", b"raw-\xff"]
        )
    )
    batches = scanner.partition(paths)
    assert 1 <= len(batches) <= 8
    prefixes = [prefix for batch in batches for prefix in batch]
    assert len(prefixes) == len(set(prefixes))
    prefixes_set = set(prefixes)
    used = set()
    for path in paths:
        parts = path.split(b"/")
        candidates = {
            path,
            *(b"/".join(parts[:depth]) + b"/" for depth in range(1, len(parts))),
        }
        matches = candidates & prefixes_set
        assert len(matches) == 1
        used.update(matches)
    assert used == prefixes_set


@pytest.mark.parametrize(
    "record",
    [
        b"invalid",
        b"040000 " + b"a" * 40 + b" 0\tdir/\0",
        b"160001 " + b"a" * 40 + b" 0\tinvalid-mode\0",
        b"100644 " + b"a" * 40 + b" 1\tunmerged\0",
        b"100644 " + b"a" * 40 + b" 0\t../escape\0",
        b"100644 " + b"a" * 40 + b" 0\t/absolute\0",
    ],
)
def test_unqualified_index_record_is_refused(record):
    with pytest.raises(ValueError, match="index"):
        scanner._paths(record)


def test_duplicate_index_paths_are_refused():
    record = b"100644 " + b"a" * 40 + b" 0\tfile\0"
    with pytest.raises(ValueError, match="ambiguous"):
        scanner._paths(record + record)


def test_index_change_during_scan_is_refused(monkeypatch):
    count = 0

    def capture(args, deadline):
        nonlocal count
        if args[0] == "ls-files":
            count += 1
            return b"100644 " + (b"a" if count == 1 else b"b") * 40 + b" 0\tfile\0"
        return b""

    monkeypatch.setattr(scanner, "_git", capture)
    with pytest.raises(ValueError, match="index changed"):
        scanner.scan()


@pytest.mark.parametrize("changed_flag", [b"h", b"S"])
def test_index_flag_change_during_scan_is_refused(monkeypatch, changed_flag):
    observations = 0

    def capture(args, deadline):
        nonlocal observations
        if args[0] != "ls-files":
            return b""
        if "--stage" in args:
            return b"100644 " + b"a" * 40 + b" 0\tfile\0"
        observations += 1
        flag = b"H" if observations == 1 else changed_flag
        return flag + b" file\0"

    monkeypatch.setattr(scanner, "_git", capture)
    with pytest.raises(ValueError, match="index changed"):
        scanner.scan()


def test_literal_arguments_and_git_failure_are_preserved(monkeypatch):
    def execute(argv, **options):
        assert argv[:2] == ["git", "--literal-pathspecs"]
        assert argv[-2:] == ["--", b":(exclude)*"]
        assert options["check"] is True and 0 < options["timeout"] <= 10
        assert options["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        raise subprocess.CalledProcessError(128, argv)

    monkeypatch.setattr(scanner.subprocess, "run", execute)
    with pytest.raises(subprocess.CalledProcessError):
        scanner._git(["diff", "--", b":(exclude)*"], scanner.time.monotonic() + 10)


def test_expired_scan_does_not_start_git(monkeypatch):
    monkeypatch.setattr(
        scanner.subprocess,
        "run",
        lambda *a, **k: pytest.fail("expired scan started Git"),
    )
    with pytest.raises(TimeoutError):
        scanner._git(["ls-files"], scanner.time.monotonic() - 1)


@pytest.mark.parametrize("command", ["ls-files", "diff"])
def test_zero_exit_with_diagnostics_never_qualifies_as_clean(
    monkeypatch, capsys, command
):
    diagnostic = b"private tracked path: Permission denied"
    monkeypatch.setattr(
        scanner.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, b"", diagnostic),
    )
    with pytest.raises(RuntimeError, match="comparison is unavailable") as error:
        scanner._git([command], scanner.time.monotonic() + 10)
    assert "private tracked path" not in str(error.value)
    output = capsys.readouterr()
    assert output.out == output.err == ""


@pytest.mark.parametrize("gitlink", [False, True])
@pytest.mark.parametrize(
    "odd",
    [
        False,
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                os.name == "nt", reason="POSIX literal colon path"
            ),
        ),
    ],
)
def test_real_git_partitioned_diff_matches_full_diff_without_index_writes(
    tmp_path, monkeypatch, odd, gitlink
):
    root = tmp_path / "one-file-git-fixture"
    root.mkdir()
    disabled = tmp_path / "disabled"
    disabled.mkdir()
    global_config = tmp_path / "fixture.gitconfig"
    global_config.write_text("", encoding="utf-8")
    excludes = tmp_path / "fixture.excludes"
    excludes.write_text("", encoding="utf-8")
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(GIT_CONFIG_GLOBAL=str(global_config), GIT_CONFIG_NOSYSTEM="1")

    def git(*args):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "core.hooksPath=" + str(disabled),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                *args,
            ],
            cwd=root,
            env=env,
            timeout=10,
        )

    names = [
        "-flag.txt",
        "literal[ab].txt",
        "space name.txt",
        "nested/a.txt",
        "nested/b.txt",
        "deeper/one/c.txt",
    ]
    if odd:
        names += [":(exclude)*.txt", "line\nname.txt"]
    git("init")
    git("config", "core.excludesFile", str(excludes))
    git("config", "core.autocrlf", "false")
    git("config", "commit.gpgSign", "true")
    git("config", "gpg.program", str(root / "unavailable-signing-program"))
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"before\n")
    git("add", "--all")
    if gitlink:
        submodule = root / "submodule"
        submodule.mkdir()
        git("-C", "submodule", "init")
        git("-C", "submodule", "config", "core.autocrlf", "false")
        (submodule / "nested.txt").write_bytes(b"nested before\n")
        git("-C", "submodule", "add", "--all")
        git("-C", "submodule", "commit", "--no-gpg-sign", "-m", "nested fixture")
        commit = git("-C", "submodule", "rev-parse", "HEAD").decode().strip()
        git("update-index", "--add", "--cacheinfo", "160000," + commit + ",submodule")
    git("commit", "--no-gpg-sign", "-m", "fixture")
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.chdir(root)
    index = git("ls-files", "--stage", "-z")
    assert scanner.scan() == b""
    if gitlink:
        from scripts.engineering.repo import offline_precommit as offline

        with monkeypatch.context() as context:
            context.setattr(offline.sys, "platform", "linux")
            with offline._read_only_staged_files(str(tmp_path)):
                pass
    for name in names:
        (root / name).write_bytes(b"after\n")
    (root / names[0]).unlink()
    if gitlink:
        (submodule / "nested.txt").write_bytes(b"nested after\n")
    actual = scanner.scan()
    expected = git("diff", "--no-ext-diff", "--no-textconv", "--ignore-submodules=none")
    assert set(actual.split(b"diff --git ")) == set(expected.split(b"diff --git "))
    assert git("ls-files", "--stage", "-z") == index
    if gitlink:
        with monkeypatch.context() as context:
            context.setattr(offline.sys, "platform", "linux")
            with pytest.raises(offline.BootstrapRequired, match="unstaged_changes"):
                with offline._read_only_staged_files(str(tmp_path)):
                    pytest.fail("dirty gitlink entered the staged-files context")
