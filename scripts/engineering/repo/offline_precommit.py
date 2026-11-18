"""Qualified pre-commit 4.7.0 adapter: cached checks, never bootstrap on Git events.

This is a command wrapper, not a network or filesystem sandbox for hook code.
Explicit installation remains a separate operator action. Unknown framework
versions fail before any configured or legacy hook executes.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from functools import partial
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys
from typing import Any
from unittest.mock import patch

QUALIFIED_VERSION = "4.7.0"
HOOK_TYPES = frozenset({"pre-commit", "pre-push", "commit-msg"})

# Tokenized entries from the qualified config; changed commands stay serial.
QUALIFIED_PUSH_COMMANDS = {
    "detect-secrets-baseline": "541f6bc8d5080ebe1fc8bcf1ab5b5e46c08f7a24948c2cefbc31b43bc6d59e5c",
    "mypy-strict": "80e2122f42a85af5847445e97e082862073e04bc725107ff5247fe4166679e98",
    "bandit": "fcf349f31c734b00281dd94f5ef8a25154826a00821ebce8f9a8fb89ede90869",
    "architecture-smoke": "00933332c815837455209c0c5d7b9c7312c0fc4248cd001dccadc6b0c07ff257",
}


class BootstrapRequired(RuntimeError):
    """A controlled failure that contains no dependency URL or secret output."""


def _store_init(store: Any, directory: str | None = None) -> None:
    store.directory = directory or store.get_default_directory()
    store.db_path = str(Path(store.directory) / "db.db")
    store.readonly = True
    if not Path(store.db_path).is_file():
        raise BootstrapRequired("cache_missing")


def _cached_repo(
    store: Any,
    repo: str,
    ref: str,
    deps: Sequence[str],
    make_strategy: Any,
) -> str:
    del make_strategy
    uri = Path(store.db_path).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=1)) as connection:
        row = connection.execute(
            "SELECT path FROM repos WHERE repo = ? AND ref = ?",
            (store.db_repo_name(repo, deps), ref),
        ).fetchone()
    if row is None or not Path(row[0]).is_dir():
        raise BootstrapRequired("repository_cache_missing")
    return str(row[0])


def _require_environments(hooks: Sequence[Any], store: Any) -> None:
    del store
    repository = importlib.import_module("pre_commit.repository")
    if any(not repository._hook_installed(hook) for hook in hooks):
        raise BootstrapRequired("environment_missing_or_unhealthy")


def _command_digest(entry: str, args: Sequence[str]) -> str:
    argv = [*shlex.split(entry), *args]
    return hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest()


def _parallel_candidates(
    module: Any,
    config: dict[str, Any],
    hooks: Sequence[Any],
    skips: set[str],
    args: Any,
) -> list[Any]:
    """Only qualified local read-only commands with no environment mutation."""
    if (
        args.hook_stage != "pre-push"
        or skips
        or len(set(QUALIFIED_PUSH_COMMANDS.values())) != len(QUALIFIED_PUSH_COMMANDS)
        or config["fail_fast"]
        or args.fail_fast
        or any(hook.fail_fast for hook in hooks)
    ):
        return []
    classifier = module.Classifier.from_config(
        module._all_filenames(args), config["files"], config["exclude"]
    )
    active = [
        hook
        for hook in hooks
        if hook.always_run or tuple(classifier.filenames_for_hook(hook))
    ]
    count = len(QUALIFIED_PUSH_COMMANDS)
    if (
        len(active) < count
        or {hook.id for hook in active[:count]} != QUALIFIED_PUSH_COMMANDS.keys()
    ):
        return []
    active = active[:count]
    if any(
        hook.src != "local"
        or hook.language != "unsupported"
        or hook.pass_filenames
        or hook.require_serial
        or _command_digest(hook.entry, hook.args) != QUALIFIED_PUSH_COMMANDS[hook.id]
        for hook in active
    ):
        return []
    return active


def _run_qualified_hooks(
    module: Any,
    serial: Any,
    config: dict[str, Any],
    hooks: Sequence[Any],
    skips: set[str],
    args: Any,
) -> int:
    """Keep framework statuses/diff checks; overlap only read-only processes."""
    active = _parallel_candidates(module, config, hooks, skips, args)
    if not active:
        return int(serial(config, hooks, skips, args))
    language = module.languages["unsupported"]
    execute = language.run_hook
    diff = module._get_diff
    baseline = diff()  # Capture before any child can run.
    first_diff = True

    def diff_with_original_baseline() -> bytes:
        nonlocal first_diff
        if first_diff:
            first_diff = False
            return baseline
        return bytes(diff())

    with ThreadPoolExecutor(max_workers=len(active)) as pool:
        pending = {}
        for hook in active:
            key = _command_digest(hook.entry, hook.args)
            expected = (hook.prefix.prefix_dir, hook.require_serial, args.color)
            future = pool.submit(
                execute,
                hook.prefix,
                hook.entry,
                hook.args,
                (),
                is_local=True,
                require_serial=hook.require_serial,
                color=args.color,
            )
            pending[key] = (expected, future)

        consumed = set()

        def completed(
            prefix: Any,
            entry: str,
            args: Sequence[str],
            file_args: Sequence[str],
            *,
            is_local: bool,
            require_serial: bool,
            color: bool,
        ) -> tuple[int, bytes]:
            key = _command_digest(entry, args)
            if key not in pending or key in consumed:
                if not all(future.done() for _, future in pending.values()):
                    raise BootstrapRequired("parallel_hook_order_changed")
                return execute(
                    prefix,
                    entry,
                    args,
                    file_args,
                    is_local=is_local,
                    require_serial=require_serial,
                    color=color,
                )
            expected, future = pending[key]
            if (
                file_args
                or not is_local
                or expected != (prefix.prefix_dir, require_serial, color)
            ):
                raise BootstrapRequired("parallel_hook_protocol_changed")
            consumed.add(key)
            return future.result()

        with (
            patch.object(language, "run_hook", completed),
            patch.object(module, "_get_diff", diff_with_original_baseline),
        ):
            return int(serial(config, hooks, skips, args))


def _qualified_contract() -> bool:
    try:
        repository = importlib.import_module("pre_commit.repository")
        Store = importlib.import_module("pre_commit.store").Store
        run_module = importlib.import_module("pre_commit.commands.run")
        lang_base = importlib.import_module("pre_commit.lang_base")
        system = run_module.languages["unsupported"]
        if (
            system.in_env is not lang_base.no_env
            or system.run_hook is not lang_base.basic_run_hook
        ):
            return False

        expected = (
            (run_module._run_hooks, ("config", "hooks", "skips", "args")),
            (run_module._get_diff, ()),
            (
                system.run_hook,
                (
                    "prefix",
                    "entry",
                    "args",
                    "file_args",
                    "is_local",
                    "require_serial",
                    "color",
                ),
            ),
            (Store.__init__, ("self", "directory")),
            (Store._new_repo, ("self", "repo", "ref", "deps", "make_strategy")),
            (repository.install_hook_envs, ("hooks", "store")),
            (repository._hook_install, ("hook",)),
            (repository._hook_installed, ("hook",)),
            (
                importlib.import_module(
                    "pre_commit.staged_files_only"
                ).staged_files_only,
                ("patch_dir",),
            ),
            (importlib.import_module("pre_commit.error_handler").error_handler, ()),
        )
        return all(
            tuple(inspect.signature(fn).parameters) == names for fn, names in expected
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def _deny_install(hook: Any) -> None:
    del hook
    raise BootstrapRequired("installation_forbidden")


@contextmanager
def _quiet_errors() -> Iterator[None]:
    """Do not let framework exception logs persist argv or child output."""
    try:
        yield
    except Exception:
        raise BootstrapRequired("framework_execution_unavailable") from None


@contextmanager
def _read_only_staged_files(patch_dir: str) -> Iterator[None]:
    """Never stash/checkout user changes in a process subject to forced kill."""
    del patch_dir
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.fsmonitor=false",
            "diff",
            "--quiet",
            "--no-ext-diff",
            "--no-textconv",
            "--ignore-submodules=none",
            "--",
        ],
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
    )
    if result.returncode:
        sys.stderr.write(
            "BioETL hook ERROR: tracked unstaged changes or unavailable diff; preserve changes explicitly outside the hook (no automatic stash).\n"
        )
        raise BootstrapRequired(
            "unstaged_changes_or_diff_unavailable_no_automatic_stash"
        )
    yield


def run(hook_type: str, hook_dir: Path, args: Sequence[str]) -> int:
    """Preserve the framework's hook protocol and legacy chain after qualification."""
    if hook_type not in HOOK_TYPES:
        return 2
    try:
        if importlib.metadata.version("pre-commit") != QUALIFIED_VERSION:
            raise BootstrapRequired("framework_version_unqualified")
        if not _qualified_contract():
            raise BootstrapRequired("framework_contract_changed")
        repository = importlib.import_module("pre_commit.repository")
        Store = importlib.import_module("pre_commit.store").Store

        offline = {
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "UV_OFFLINE": "true",
            "NPM_CONFIG_OFFLINE": "true",
            "GIT_ALLOW_PROTOCOL": "file",
        }
        with (
            patch.object(Store, "__init__", _store_init),
            patch.object(Store, "_new_repo", _cached_repo),
            patch.object(repository, "install_hook_envs", _require_environments),
            patch.object(repository, "_hook_install", _deny_install),
            patch.dict(os.environ, offline),
        ):
            # Import after patches: commands.run binds install_hook_envs at import.
            # Patch its alias too when another caller has already imported it.
            run_module = importlib.import_module("pre_commit.commands.run")
            framework_main = importlib.import_module("pre_commit.main")
            serial = run_module._run_hooks

            with (
                patch.object(run_module, "install_hook_envs", _require_environments),
                patch.object(framework_main, "error_handler", _quiet_errors),
                patch.object(run_module, "staged_files_only", _read_only_staged_files),
                patch.object(
                    run_module,
                    "_run_hooks",
                    partial(_run_qualified_hooks, run_module, serial),
                ),
            ):
                return int(
                    framework_main.main(
                        [
                            "hook-impl",
                            "--config",
                            ".pre-commit-config.yaml",
                            "--hook-type",
                            hook_type,
                            "--hook-dir",
                            str(hook_dir),
                            "--",
                            *args,
                        ]
                    )
                )
    except (
        BootstrapRequired,
        importlib.metadata.PackageNotFoundError,
        ImportError,
        OSError,
        sqlite3.Error,
        subprocess.SubprocessError,
        ValueError,
        TypeError,
    ):
        sys.stderr.write(
            "BioETL hook ERROR: qualified framework/configuration/dependencies unavailable; "
            "run the explicit hook bootstrap outside the Git operation.\n"
        )
        return 2


def main() -> int:
    if len(sys.argv) < 3:
        return 2
    return run(sys.argv[1], Path(sys.argv[2]), sys.argv[3:])


if __name__ == "__main__":
    raise SystemExit(main())
