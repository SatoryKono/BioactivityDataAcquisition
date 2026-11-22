"""Linux diff coalescing keeps actual checks and fails closed on changed state."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml

from scripts.engineering.repo.offline_precommit import _CoalescedPrecommit as adapter
from scripts.engineering.repo import offline_precommit as offline

pytestmark = pytest.mark.unit


@pytest.fixture
def framework(monkeypatch, tmp_path):
    from pre_commit.commands import run as module
    from pre_commit.lang_base import no_env

    source = "https://github.com/pre-commit/pre-commit-hooks"
    hooks = [
        SimpleNamespace(
            id=name,
            name=name,
            alias="",
            src=source,
            language="python",
            entry=entry,
            args=(),
            prefix=SimpleNamespace(prefix_dir="cache"),
            pass_filenames=True,
            require_serial=False,
            fail_fast=False,
            always_run=False,
            verbose=False,
            log_file="",
            language_version="default",
        )
        for name, entry in [
            ("trailing-whitespace", "trailing-whitespace-fixer"),
            ("end-of-file-fixer", "end-of-file-fixer"),
        ]
    ]
    classifier = SimpleNamespace(filenames_for_hook=lambda h: ("fixture.txt",))
    monkeypatch.setattr(
        module, "Classifier", SimpleNamespace(from_config=lambda *a: classifier)
    )
    monkeypatch.setattr(module, "_all_filenames", lambda args: ("fixture.txt",))
    legacy = Mock(return_value=b"")
    scan = Mock(return_value=b"")
    monkeypatch.setattr(module, "_get_diff", legacy)
    monkeypatch.setattr(adapter, "_fresh_diff", scan)
    monkeypatch.setattr(adapter, "_sources_match", lambda root: True)
    monkeypatch.setattr(adapter.sys, "platform", "linux")
    results = {}
    execute = Mock(
        side_effect=lambda prefix, entry, *a, **k: (results.get(entry, 0), b"")
    )
    language = SimpleNamespace(in_env=no_env, run_hook=execute)
    monkeypatch.setattr(module, "languages", {"python": language})
    args = SimpleNamespace(
        hook_stage="pre-commit",
        fail_fast=False,
        color=False,
        verbose=False,
        all_files=False,
        show_diff_on_failure=False,
    )
    config = {
        "files": "",
        "exclude": "^$",
        "fail_fast": False,
        "repos": [{"repo": source, "rev": "v6.0.0"}],
    }
    return SimpleNamespace(
        module=module,
        hooks=hooks,
        args=args,
        config=config,
        root=tmp_path,
        execute=execute,
        scan=scan,
        legacy=legacy,
        language=language,
        results=results,
        skips=set(),
    )


def invoke(f, initial_clean=True):
    return adapter.dispatch(
        f.module,
        f.module._run_hooks,
        f.config,
        f.hooks,
        f.skips,
        f.args,
        root=f.root,
        initial_clean=initial_clean,
    )


def test_success_runs_every_command_then_checks_fresh_final_diff(framework):
    f = framework
    assert invoke(f) == 0
    assert f.execute.call_count == 2
    f.scan.assert_called_once()
    f.legacy.assert_not_called()
    assert f.language.run_hook is f.execute and f.module._get_diff is f.legacy


def test_unexpected_write_with_zero_exit_is_rejected(framework):
    f = framework
    f.scan.return_value = b"changed source"
    assert invoke(f) == 1
    assert f.execute.call_count == 2


def test_formatter_failure_resumes_per_hook_diff_checks(framework):
    f = framework
    f.results[f.hooks[0].entry] = 1
    f.scan.side_effect = [b"formatter changed source", b"formatter changed source"]
    assert invoke(f) == 1
    assert f.execute.call_count == 2 and f.scan.call_count == 2


def test_unavailable_final_diff_cannot_pass_and_patches_restore(framework):
    f = framework
    f.scan.side_effect = OSError("diff unavailable")
    with pytest.raises(OSError, match="unavailable"):
        invoke(f)
    assert f.language.run_hook is f.execute and f.module._get_diff is f.legacy


@pytest.mark.parametrize(
    "change",
    [
        "platform",
        "stage",
        "skip",
        "fail-fast",
        "command",
        "revision",
        "duplicate-repository",
        "unknown",
        "source",
        "initial-state",
    ],
)
def test_unqualified_contract_retains_ordinary_framework(
    framework, monkeypatch, change
):
    f = framework
    initial = True
    if change == "platform":
        monkeypatch.setattr(adapter.sys, "platform", "win32")
    elif change == "stage":
        f.args.hook_stage = "pre-push"
    elif change == "skip":
        f.skips.add(f.hooks[0].id)
    elif change == "fail-fast":
        f.args.fail_fast = True
    elif change == "command":
        f.hooks[0].args = ("--unknown",)
    elif change == "revision":
        f.config["repos"][0]["rev"] = "unqualified"
    elif change == "duplicate-repository":
        f.config["repos"].append(dict(f.config["repos"][0]))
    elif change == "unknown":
        f.hooks[0].id = "unqualified"
    elif change == "source":
        monkeypatch.setattr(adapter, "_sources_match", lambda root: False)
    else:
        initial = False
    invoke(f, initial)
    f.scan.assert_not_called()
    assert f.legacy.call_count >= 2


def test_command_change_after_qualification_is_rejected_before_execution(
    framework, monkeypatch
):
    f = framework

    def serial(*args):
        f.hooks[0].entry = "unqualified command"
        return f.module._run_hooks(*args)

    with pytest.raises(ValueError, match="execution_contract"):
        adapter.dispatch(
            f.module,
            serial,
            f.config,
            f.hooks,
            f.skips,
            f.args,
            root=f.root,
            initial_clean=True,
        )
    f.execute.assert_not_called()


def test_project_pins_match_current_sources_and_fail_on_write_formatter_argument():
    root = Path(__file__).resolve().parents[3]
    assert adapter._sources_match(root)
    config = yaml.safe_load((root / ".pre-commit-config.yaml").read_text())
    for repository in config["repos"]:
        if repository["repo"] in adapter.REVISIONS:
            assert adapter.REVISIONS[repository["repo"]] == repository["rev"]
    hook = next(
        h for r in config["repos"] for h in r["hooks"] if h["id"] == "ruff-format"
    )
    assert hook["args"] == ["--exit-non-zero-on-format"]
    assert (
        adapter._digest("ruff format --force-exclude", hook["args"])
        == adapter.COMMANDS["ruff-format"][2]
    )


@pytest.mark.parametrize(
    ("hook_id", "entry"),
    [
        ("ruff", "ruff check --force-exclude"),
        ("ruff-format", "ruff format --force-exclude"),
    ],
)
def test_current_python_hooks_qualify_and_unknown_revision_falls_back(
    framework, hook_id, entry
):
    f = framework
    root = Path(__file__).resolve().parents[3]
    configured = yaml.safe_load((root / ".pre-commit-config.yaml").read_text())
    repository = next(
        r
        for r in configured["repos"]
        if r["repo"] == "https://github.com/astral-sh/ruff-pre-commit"
    )
    hook_config = next(h for h in repository["hooks"] if h["id"] == hook_id)
    hook = SimpleNamespace(**vars(f.hooks[0]))
    hook.id = hook.name = hook_id
    hook.src = repository["repo"]
    hook.entry = entry
    hook.args = tuple(hook_config["args"])
    hook.require_serial = True
    f.hooks = [hook]
    f.config["repos"] = [repository]
    assert adapter.qualified(f.module, f.config, f.hooks, f.skips, f.args, root)
    assert invoke(f) == 0
    f.execute.assert_called_once()
    f.scan.assert_called_once()
    f.legacy.assert_not_called()

    # A future, unqualified pin must retain ordinary per-hook diff checks.
    repository["rev"] = "unqualified-future-version"
    f.scan.reset_mock()
    assert not adapter.qualified(f.module, f.config, f.hooks, f.skips, f.args, root)
    assert invoke(f) == 0
    f.scan.assert_not_called()
    assert f.legacy.call_count >= 2


def test_linux_environment_probe_deduplication_is_exact_and_never_cross_event(
    monkeypatch,
):
    from pre_commit import repository

    monkeypatch.setattr(offline.sys, "platform", "linux")
    checks = Mock(return_value=True)
    monkeypatch.setattr(repository, "_hook_installed", checks)
    hooks = [
        SimpleNamespace(install_key=("cache", "python", "default", deps))
        for deps in [(), (), ("extra",)]
    ]
    offline._require_environments(hooks, None)
    offline._require_environments(hooks, None)
    assert checks.call_count == 4
    checks.side_effect = lambda hook: hook.install_key[-1] != ("extra",)
    with pytest.raises(offline.BootstrapRequired, match="unhealthy"):
        offline._require_environments(hooks, None)


@pytest.mark.parametrize("kind", ["backend", "scanner"])
def test_owned_backend_loaders_do_not_accept_stale_bytecode(
    tmp_path, monkeypatch, kind
):
    import importlib.util
    from importlib._bootstrap_external import _code_to_timestamp_pyc

    folder = tmp_path / "scripts" / "engineering" / "repo"
    folder.mkdir(parents=True)
    source = tmp_path / offline.BACKEND_PATHS["partitioned_diff"]
    source.write_text(
        'class _SourceDiffScanner:\n    @staticmethod\n    def scan(): return b"source"\n'
    )
    info = source.stat()
    cache = Path(importlib.util.cache_from_source(str(source)))
    cache.parent.mkdir(parents=True, exist_ok=True)
    stale = compile(
        'class _SourceDiffScanner:\n    @staticmethod\n    def scan(): return b"cached"',
        str(source),
        "exec",
    )
    cache.write_bytes(_code_to_timestamp_pyc(stale, int(info.st_mtime), info.st_size))
    if kind == "backend":
        monkeypatch.setattr(
            offline, "__file__", str(folder / Path(offline.__file__).name)
        )
        actual = offline._message_backend("partitioned_diff").scan()
    else:
        monkeypatch.setattr(
            adapter, "__file__", str(folder / Path(adapter.__file__).name)
        )
        actual = adapter._fresh_diff()
    assert actual == b"source"


def test_configured_log_writer_is_not_a_qualified_readonly_command(framework):
    f = framework
    f.hooks[0].log_file = str(f.root / "hook.log")
    assert invoke(f) == 0
    f.scan.assert_not_called()
    assert f.legacy.call_count == 3
