"""Concurrency must preserve framework failure and mutation detection semantics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml

from scripts.engineering.repo import offline_precommit as adapter

pytestmark = pytest.mark.unit


@pytest.fixture
def parallel_framework(monkeypatch, tmp_path):
    from pre_commit.commands import run as module
    from pre_commit.lang_base import no_env

    hooks = [
        SimpleNamespace(
            id=name,
            alias="",
            name=name,
            entry=f"fixture {name}",
            args=(),
            src="local",
            prefix=SimpleNamespace(prefix_dir=str(tmp_path)),
            language="unsupported",
            language_version="default",
            pass_filenames=False,
            require_serial=False,
            fail_fast=False,
            always_run=False,
            verbose=False,
            log_file=None,
        )
        for name in adapter.QUALIFIED_PUSH_COMMANDS
    ]
    pins = {h.id: adapter._command_digest(h.entry, h.args) for h in hooks}
    monkeypatch.setattr(adapter, "QUALIFIED_PUSH_COMMANDS", pins)
    classifier = SimpleNamespace(filenames_for_hook=lambda hook: ("fixture.txt",))
    monkeypatch.setattr(
        module, "Classifier", SimpleNamespace(from_config=lambda *a: classifier)
    )
    monkeypatch.setattr(module, "_all_filenames", lambda args: ("fixture.txt",))
    diffs = Mock(return_value=b"")
    monkeypatch.setattr(module, "_get_diff", diffs)
    barrier = threading.Barrier(len(hooks))
    calls, finished = [], set()
    failures = {}

    def execute(prefix, entry, args, file_args, **kwargs):
        assert not file_args and kwargs["is_local"]
        if entry in finished or not entry.startswith("fixture "):
            assert len(finished) == len(hooks)
        else:
            barrier.wait(timeout=5)  # All four subprocess slots must start.
        calls.append(entry)
        finished.add(entry)
        return failures.get(entry, 0), b""

    language = SimpleNamespace(run_hook=execute, in_env=no_env)
    monkeypatch.setattr(module, "languages", {"unsupported": language})
    args = SimpleNamespace(
        hook_stage="pre-push",
        fail_fast=False,
        verbose=False,
        color=False,
        show_diff_on_failure=False,
        all_files=False,
    )
    config = {"files": "", "exclude": "^$", "fail_fast": False}
    return SimpleNamespace(
        module=module,
        hooks=hooks,
        args=args,
        config=config,
        diffs=diffs,
        calls=calls,
        failures=failures,
        language=language,
        execute=execute,
    )


def invoke(f):
    return adapter._run_qualified_hooks(
        f.module, f.module._run_hooks, f.config, f.hooks, set(), f.args
    )


@pytest.mark.parametrize(
    "failure,mutation", [(False, False), (True, False), (False, True)]
)
def test_parallel_checks_keep_framework_exit_and_every_diff(
    parallel_framework, failure, mutation
):
    f = parallel_framework
    if failure:
        f.failures[f.hooks[1].entry] = 7
    if mutation:
        f.diffs.side_effect = [b"", b"modified", b"modified", b"modified", b"modified"]
    assert invoke(f) == int(failure or mutation)
    assert Counter(f.calls) == Counter(h.entry for h in f.hooks)
    assert f.diffs.call_count == len(f.hooks) + 1
    assert f.module._get_diff is f.diffs
    assert f.language.run_hook is f.execute


def test_later_hook_runs_normally_after_parallel_checks(parallel_framework):
    f = parallel_framework
    extra = SimpleNamespace(**vars(f.hooks[0]))
    extra.id, extra.name, extra.entry = "extra", "extra", "after qualified checks"
    # A later mutator must still be detected by the framework's own diff check.
    f.hooks = [*f.hooks, extra]
    f.diffs.side_effect = [b"", b"", b"", b"", b"", b"modified by extra"]
    assert invoke(f) == 1
    assert f.calls[-1] == extra.entry
    assert len(f.calls) == 5


@pytest.mark.parametrize(
    "change",
    [
        "pre-commit",
        "skip",
        "config-fast",
        "args-fast",
        "hook-fast",
        "command",
        "language",
        "filenames",
        "serial",
        "prefix",
        "duplicate",
    ],
)
def test_unqualified_schedules_stay_serial(parallel_framework, change):
    f = parallel_framework
    skips = set()
    if change == "pre-commit":
        f.args.hook_stage = "pre-commit"
    elif change == "skip":
        skips.add(f.hooks[0].id)
    elif change == "config-fast":
        f.config["fail_fast"] = True
    elif change == "args-fast":
        f.args.fail_fast = True
    elif change == "hook-fast":
        f.hooks[0].fail_fast = True
    elif change == "command":
        f.hooks[0].entry += " changed"
    elif change == "language":
        f.hooks[0].language = "python"
    elif change == "filenames":
        f.hooks[0].pass_filenames = True
    elif change == "duplicate":
        f.hooks[1].entry = f.hooks[0].entry
        adapter.QUALIFIED_PUSH_COMMANDS[f.hooks[1].id] = (
            adapter.QUALIFIED_PUSH_COMMANDS[f.hooks[0].id]
        )
    elif change == "serial":
        f.hooks[0].require_serial = True
    else:
        extra = SimpleNamespace(**vars(f.hooks[0]))
        extra.id, extra.entry = "early", "early unqualified check"
        f.hooks = [extra, *f.hooks]
    serial = Mock(return_value=23)
    assert (
        adapter._run_qualified_hooks(f.module, serial, f.config, f.hooks, skips, f.args)
        == 23
    )
    serial.assert_called_once_with(f.config, f.hooks, skips, f.args)
    assert not f.calls
    f.diffs.assert_not_called()


def test_current_command_qualification_is_source_bound():
    root = Path(adapter.__file__).resolve().parents[3]
    config = yaml.safe_load((root / ".pre-commit-config.yaml").read_text())
    hooks = {h["id"]: h for r in config["repos"] for h in r["hooks"]}
    for name, fingerprint in adapter.QUALIFIED_PUSH_COMMANDS.items():
        h = hooks[name]
        assert h["stages"] == ["pre-push"]
        assert h["language"] == "system" and h["pass_filenames"] is False
        assert adapter._command_digest(h["entry"], h.get("args", ())) == fingerprint


@pytest.mark.parametrize("missing", [False, True])
def test_dispatch_contract_drift_refuses_before_framework_main(
    monkeypatch, tmp_path, missing
):
    from pre_commit.commands import run as module
    from pre_commit import main

    execute = Mock(side_effect=AssertionError("framework must not execute"))
    monkeypatch.setattr(main, "main", execute)
    if missing:
        monkeypatch.delattr(module, "_get_diff")
    else:
        monkeypatch.setattr(module, "_get_diff", lambda unsupported_argument: b"")
    assert adapter.run("pre-push", tmp_path, []) == 2
    execute.assert_not_called()


def test_python_environment_is_entered_only_after_parallel_checks(parallel_framework):
    from contextlib import contextmanager

    f = parallel_framework
    extra = SimpleNamespace(**vars(f.hooks[0]))
    extra.id, extra.name, extra.entry = (
        "python-extra",
        "python-extra",
        "after core checks",
    )
    extra.language = "python"
    entered = []

    @contextmanager
    def in_env(prefix, version):
        assert len(f.calls) == 4
        entered.append(True)
        yield

    f.module.languages["python"] = SimpleNamespace(in_env=in_env, run_hook=f.execute)
    f.hooks = [*f.hooks, extra]
    assert invoke(f) == 0
    assert entered == [True] and f.calls[-1] == extra.entry


def test_framework_exception_restores_patches_and_drains_workers(parallel_framework):
    f = parallel_framework

    def broken(config, hooks, skips, args):
        raise RuntimeError("fixture framework failure")

    with pytest.raises(RuntimeError, match="fixture framework failure"):
        adapter._run_qualified_hooks(f.module, broken, f.config, f.hooks, set(), f.args)
    assert f.module._get_diff is f.diffs
    assert f.language.run_hook is f.execute
    assert len(f.calls) == 4
