"""The metadata-only message adapter is source bound and preserves CLI results."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml

from scripts.engineering.repo.hook_installation import _ReadOnlyMessage as reader

pytestmark = pytest.mark.unit


@pytest.fixture
def message_checkout(tmp_path, monkeypatch):
    source = Path(reader.__file__).resolve()
    project = source.parents[3]
    root = tmp_path / "checkout with spaces"
    root.mkdir()
    for relative in reader.SOURCE_HASHES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((project / relative).read_bytes())
    (root / "pyproject.toml").write_text("")
    config = yaml.safe_load((project / ".pre-commit-config.yaml").read_text())
    hook = next(
        h for r in config["repos"] for h in r["hooks"] if h["id"] == reader.HOOK_ID
    )
    (root / ".pre-commit-config.yaml").write_text(
        json.dumps({"repos": [{"repo": "local", "hooks": [hook]}]})
    )
    bundle = root / "metadata/bioetl-hooks/candidate"
    own = bundle / "scripts/engineering/repo/hook_installation.py"
    own.parent.mkdir(parents=True)
    own.write_bytes(source.read_bytes())
    manifest = json.dumps(
        {
            "version": 1,
            "files": {
                "scripts/engineering/repo/hook_installation.py": hashlib.sha256(
                    own.read_bytes()
                ).hexdigest()
            },
        }
    ).encode()
    (bundle / "manifest.json").write_bytes(manifest)
    hooks = root / "metadata/hooks"
    hooks.mkdir()
    state = {
        "version": 1,
        "bundle": str(bundle),
        "python": sys.executable,
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "hooks": {
            kind: {"chain_foreign": False}
            for kind in ("pre-commit", "pre-push", "commit-msg")
        },
    }
    state_path = hooks / ".bioetl-hooks-state.json"
    state_path.write_text(json.dumps(state))
    message = root / "metadata/COMMIT_EDITMSG"
    message.write_text("docs(hooks): preserve source-bound execution\n")
    monkeypatch.setattr(reader, "__file__", str(own))
    monkeypatch.setenv("BIOETL_HOOK_PROJECT_PYTHON", sys.executable)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.delenv("SKIP", raising=False)
    return SimpleNamespace(
        root=root,
        hooks=hooks,
        state=state,
        state_path=state_path,
        message=message,
        own=own,
        hook=hook,
    )


@pytest.mark.parametrize("header", ["docs(hooks): valid header", "invalid header", ""])
def test_semantic_execution_matches_the_original_cli_and_preserves_sources(
    message_checkout, header
):
    f = message_checkout
    f.message.write_text(header + "\n")
    assert reader.qualified(f.root, f.hooks)
    before = {name: sys.modules.get(name) for name, _ in reader.MODULES}
    path = sys.path[:]
    files = {name: (f.root / name).read_bytes() for name in reader.SOURCE_HASHES}
    result = reader._invoke(f.root, str(f.message))
    env = dict(os.environ, PYTHONPATH=str(f.root))
    actual = subprocess.run(
        [
            sys.executable,
            str(f.root / "scripts/engineering/dev/run_project_python.py"),
            "-m",
            "scripts.engineering.dev.check_commit_message",
            str(f.message),
        ],
        cwd=f.root,
        env=env,
        capture_output=True,
        timeout=10,
    )
    assert result[0] == actual.returncode
    assert result[1].replace(b"\r\n", b"\n") == (actual.stdout + actual.stderr).replace(
        b"\r\n", b"\n"
    )
    assert all(sys.modules.get(name) is value for name, value in before.items())
    assert sys.path == path
    assert all((f.root / name).read_bytes() == data for name, data in files.items())
    assert f.message.read_text() == header + "\n"


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "foreign",
        "legacy",
        "interpreter",
        "manifest",
        "version",
        "command",
        "extra",
        "skip",
        "log_file",
    ],
)
def test_unqualified_message_contract_never_uses_semantic_execution(
    message_checkout, monkeypatch, change
):
    f = message_checkout
    if change == "source":
        p = f.root / "scripts/engineering/dev/check_commit_message.py"
        p.write_bytes(p.read_bytes() + b"\n# unqualified source\n")
    elif change == "foreign":
        f.state["hooks"]["commit-msg"]["chain_foreign"] = True
    elif change == "legacy":
        (f.hooks / "commit-msg.legacy").write_text("fixture")
    elif change == "log_file":
        p = f.root / ".pre-commit-config.yaml"
        config = yaml.safe_load(p.read_text())
        config["repos"][0]["hooks"][0]["log_file"] = "unexpected.log"
        p.write_text(json.dumps(config))
    elif change == "interpreter":
        monkeypatch.setenv("BIOETL_HOOK_PROJECT_PYTHON", str(f.root / "other-python"))
    elif change == "manifest":
        f.state["manifest_sha256"] = "0" * 64
    elif change == "version":
        f.state["version"] = 2
    elif change in {"command", "extra"}:
        p = f.root / ".pre-commit-config.yaml"
        config = yaml.safe_load(p.read_text())
        if change == "command":
            config["repos"][0]["hooks"][0]["entry"] += " --unknown"
        else:
            config["repos"][0]["hooks"].append({**f.hook, "id": "unknown-extra"})
        p.write_text(json.dumps(config))
    else:
        monkeypatch.setenv("SKIP", reader.HOOK_ID)
    f.state_path.write_text(json.dumps(f.state))
    assert reader.qualified(f.root, f.hooks) is False


def test_framework_status_is_preserved_without_spawning_or_diff_scans(
    message_checkout, monkeypatch
):
    from pre_commit.commands import run as module
    from pre_commit.lang_base import no_env

    f = message_checkout
    hook = SimpleNamespace(
        id=reader.HOOK_ID,
        name="header",
        alias="",
        src="local",
        language="python",
        entry=f.hook["entry"],
        args=(),
        prefix=SimpleNamespace(prefix_dir="fixture-cache"),
        pass_filenames=True,
        require_serial=False,
        language_version="default",
        always_run=False,
        verbose=False,
        log_file="",
        fail_fast=False,
    )
    classifier = SimpleNamespace(filenames_for_hook=lambda h: (str(f.message),))
    monkeypatch.setattr(
        module, "Classifier", SimpleNamespace(from_config=lambda *a: classifier)
    )
    monkeypatch.setattr(module, "_all_filenames", lambda args: (str(f.message),))
    scan = Mock(
        side_effect=AssertionError("metadata checker must not scan source worktree")
    )
    launch = Mock(side_effect=AssertionError("source-pinned parser must not spawn"))
    language = SimpleNamespace(in_env=no_env, run_hook=launch)
    monkeypatch.setattr(module, "_get_diff", scan)
    monkeypatch.setattr(module, "languages", {"python": language})
    config = {"files": "", "exclude": "^$", "fail_fast": False}
    args = SimpleNamespace(
        hook_stage="commit-msg",
        fail_fast=False,
        verbose=False,
        color=False,
        show_diff_on_failure=False,
        all_files=False,
    )
    for text, expected in (("docs(hooks): valid\n", 0), ("invalid\n", 1)):
        f.message.write_text(text)
        assert (
            reader.dispatch(
                module,
                module._run_hooks,
                config,
                [hook],
                set(),
                args,
                root=f.root,
                hook_dir=f.hooks,
            )
            == expected
        )
    scan.assert_not_called()
    launch.assert_not_called()
    assert module._get_diff is scan and language.run_hook is launch
    monkeypatch.setattr(classifier, "filenames_for_hook", lambda h: ())
    with pytest.raises(ValueError, match="not_executed"):
        reader.dispatch(
            module,
            module._run_hooks,
            config,
            [hook],
            set(),
            args,
            root=f.root,
            hook_dir=f.hooks,
        )


@pytest.mark.parametrize("outside", [False, True])
def test_semantic_message_input_cannot_be_an_option_or_worktree_file(
    message_checkout, outside
):
    f = message_checkout
    if outside:
        p = f.root / "tracked-source.py"
        p.write_text("docs(hooks): metadata required\n")
        name = str(p)
    else:
        name = "--help"
    with pytest.raises(ValueError, match="outside_metadata"):
        reader._invoke(f.root, name)


def test_stale_bytecode_cannot_override_the_verified_message_source(message_checkout):
    import importlib.util
    from importlib._bootstrap_external import _code_to_timestamp_pyc

    f = message_checkout
    relative = reader.MODULES[-1][1]
    source = f.root / relative
    code = compile("def main(argv): return 0", str(source), "exec")
    stat = source.stat()
    cache = Path(importlib.util.cache_from_source(str(source)))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(_code_to_timestamp_pyc(code, int(stat.st_mtime), stat.st_size))
    f.message.write_text("invalid header\n")
    assert reader._invoke(f.root, str(f.message))[0] == 1


@pytest.mark.parametrize(
    "filters",
    [{}, {"types": ["python"]}, {"types_or": ["python"]}, {"exclude_types": ["text"]}],
)
def test_real_classifier_preserves_filtered_message_skip(
    message_checkout, monkeypatch, filters
):
    from pre_commit.commands import run as module
    from pre_commit.lang_base import no_env

    f = message_checkout
    config_path = f.root / ".pre-commit-config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["repos"][0]["hooks"][0].update(filters)
    config_path.write_text(json.dumps(config))
    hook = SimpleNamespace(
        id=reader.HOOK_ID,
        name="header",
        alias="",
        src="local",
        language="python",
        entry=f.hook["entry"],
        args=(),
        prefix=SimpleNamespace(prefix_dir="fixture-cache"),
        pass_filenames=True,
        require_serial=False,
        language_version="default",
        always_run=False,
        verbose=False,
        log_file="",
        fail_fast=False,
        files="",
        exclude="^$",
        types=filters.get("types", ["file"]),
        types_or=filters.get("types_or", []),
        exclude_types=filters.get("exclude_types", []),
    )
    args = SimpleNamespace(
        hook_stage="commit-msg",
        commit_msg_filename=str(f.message),
        fail_fast=False,
        verbose=False,
        color=False,
        show_diff_on_failure=False,
        all_files=False,
    )
    scan = Mock(return_value=b"")
    launch = Mock(side_effect=AssertionError("filtered checker must not execute"))
    monkeypatch.setattr(module, "_get_diff", scan)
    monkeypatch.setattr(
        module, "languages", {"python": SimpleNamespace(in_env=no_env, run_hook=launch)}
    )
    runtime_config = {"files": "", "exclude": "^$", "fail_fast": False}
    # Use the real framework Classifier and commit-msg filename selection.
    assert bool(
        tuple(
            module.Classifier.from_config(
                (str(f.message),), "", "^$"
            ).filenames_for_hook(hook)
        )
    ) == (not filters)
    assert reader.qualified(f.root, f.hooks) == (not filters)
    if filters:
        assert module._run_hooks(runtime_config, [hook], set(), args) == 0
        assert scan.called
    else:
        assert (
            reader.dispatch(
                module,
                module._run_hooks,
                runtime_config,
                [hook],
                set(),
                args,
                root=f.root,
                hook_dir=f.hooks,
            )
            == 0
        )
        scan.assert_not_called()
    launch.assert_not_called()
