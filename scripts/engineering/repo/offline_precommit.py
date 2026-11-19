"""Qualified pre-commit 4.7.0 adapter: cached checks, never bootstrap on Git events.

This is a command wrapper, not a network or filesystem sandbox for hook code.
Explicit installation remains a separate operator action. Unknown framework
versions fail before any configured or legacy hook executes.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, closing, contextmanager
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys
from typing import Any, ClassVar
from unittest.mock import patch

QUALIFIED_VERSION = "4.7.0"
HOOK_TYPES = frozenset({"pre-commit", "pre-push", "commit-msg"})
BACKEND_PATHS = {
    "partitioned_diff": "scripts/engineering/repo/hook_receipts.py",
    "readonly_message": "scripts/engineering/repo/hook_installation.py",
    "coalesced_precommit": "scripts/engineering/repo/offline_precommit.py",
}


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
    seen = set()
    for hook in hooks:
        # Exact framework environment identity, only within this invocation.
        key = getattr(hook, "install_key", None) if sys.platform == "linux" else None
        if key is not None and key in seen:
            continue
        if not repository._hook_installed(hook):
            raise BootstrapRequired("environment_missing_or_unhealthy")
        if key is not None:
            seen.add(key)


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
    if sys.platform == "linux":
        changed = bool(_message_backend("partitioned_diff").scan())
    else:
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
        changed = bool(result.returncode)
    if changed:
        sys.stderr.write(
            "BioETL hook ERROR: tracked unstaged changes or unavailable diff; preserve changes explicitly outside the hook (no automatic stash).\n"
        )
        raise BootstrapRequired(
            "unstaged_changes_or_diff_unavailable_no_automatic_stash"
        )
    yield


def _message_backend(name: str = "readonly_message") -> Any:
    try:
        source = Path(__file__).resolve().parents[3] / BACKEND_PATHS[name]
        spec = importlib.util.spec_from_file_location("_bioetl_owned_message", source)
        if spec is None or spec.loader is None:
            raise BootstrapRequired("message_backend_unavailable")
        module = importlib.util.module_from_spec(spec)
        exec(compile(source.read_bytes(), str(source), "exec"), module.__dict__)
        return getattr(
            module,
            {
                "partitioned_diff": "_SourceDiffScanner",
                "readonly_message": "_ReadOnlyMessage",
                "coalesced_precommit": "_CoalescedPrecommit",
            }[name],
        )
    except Exception:
        raise BootstrapRequired("message_backend_unavailable") from None


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

        root = Path.cwd()
        message = _message_backend() if hook_type == "commit-msg" else None
        readonly = bool(message is not None and message.qualified(root, hook_dir))
        commit = (
            _message_backend("coalesced_precommit")
            if hook_type == "pre-commit" and sys.platform == "linux"
            else None
        )
        initial_clean = False

        @contextmanager
        def staged_files(patch_dir: str) -> Iterator[None]:
            nonlocal initial_clean
            if readonly:
                yield  # Verified header code reads metadata; no source hiding.
            else:
                with _read_only_staged_files(patch_dir):
                    initial_clean = True
                    yield

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

            def dispatch(config: Any, hooks: Any, skips: Any, options: Any) -> int:
                if readonly:
                    return int(
                        message.dispatch(
                            run_module,
                            serial,
                            config,
                            hooks,
                            skips,
                            options,
                            root=root,
                            hook_dir=hook_dir,
                        )
                    )
                if commit is not None:
                    return commit.dispatch(
                        run_module,
                        serial,
                        config,
                        hooks,
                        skips,
                        options,
                        root=root,
                        initial_clean=initial_clean,
                    )
                return _run_qualified_hooks(
                    run_module, serial, config, hooks, skips, options
                )

            with (
                patch.object(run_module, "install_hook_envs", _require_environments),
                patch.object(framework_main, "error_handler", _quiet_errors),
                patch.object(run_module, "staged_files_only", staged_files),
                patch.object(run_module, "_run_hooks", dispatch),
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


class _CoalescedPrecommit:
    """Bounded Linux diff coalescing for checks that fail whenever they modify input."""

    __file__ = __file__
    sys = sys

    COMMANDS: ClassVar[dict[str, tuple[str, str, str, bool]]] = {
        "ruff": (
            "https://github.com/astral-sh/ruff-pre-commit",
            "python",
            "058b76ab83ce812afb3b564d2a7b8979f9c1e7ea4959cbdb03a6e31dffbefc43",
            True,
        ),
        "ruff-format": (
            "https://github.com/astral-sh/ruff-pre-commit",
            "python",
            "19c68d5c1d04363ee497349601264f36aadecbec337bf315ef1496d2d0c1e420",
            True,
        ),
        "trailing-whitespace": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "2dccb1abe2d10a3d243b14427d3f0bd786a020b1b1992d19441bed658244b3fb",
            False,
        ),
        "end-of-file-fixer": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "f1135a580d7aaeaa3a2501872e251b403bc7204d33f79a08fd6b54205877b817",
            False,
        ),
        "check-yaml": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "9878aa39daadbec8a5f6b2ac969bd1e6dd8446901546c54388d2cfd6a644ffb8",
            False,
        ),
        "check-json": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "55aa3dad7ac07ad17b0fc1d8c7b4de8daebcdf8975699b04e2f6b77e8ccdad9f",
            False,
        ),
        "check-toml": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "6269b40f48cd36b82d763eec0833be6a666eaef05a351838260f9fa319e98597",
            False,
        ),
        "check-added-large-files": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "fca94c4cb238290fae8a8653009330f32d711dfee41266d48e7910f3b2555e18",
            False,
        ),
        "check-case-conflict": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "ff0aa28b37ddeb9925b98c2ff3ef5ab3b634f739ed9665367b23e1f39fb6367a",
            False,
        ),
        "check-merge-conflict": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "355998e06494efec4529f11e3744fbcc63e7a510406cb9d7908a6b2cd592b498",
            False,
        ),
        "debug-statements": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "485087f1c041043f6043446681775cac98c110f0e5a58feb6af71f72349b88c9",
            False,
        ),
        "mixed-line-ending": (
            "https://github.com/pre-commit/pre-commit-hooks",
            "python",
            "171d5c793e7681d32a03aff230ad1fd0ebc95d7e96ff50b45329db2f71e31695",
            False,
        ),
        "forbid-cache-files": (
            "local",
            "pygrep",
            "5060bb8d0a1735abb0b5f21a5ae821ee4f95e30539485626119cd9ae5d2e04c4",
            False,
        ),
        "forbid-env-files": (
            "local",
            "pygrep",
            "8a81d3d47b795987d060e540482a3b008d2713198e1ba05d36c957e317a29cd7",
            False,
        ),
        "audit-root-cleanliness": (
            "local",
            "python",
            "8cc5283ae519a317c15356ae7245a6cf11654816df7f4bd814587032eb015546",
            False,
        ),
    }

    SOURCES: ClassVar[dict[str, str]] = {
        "scripts/__init__.py": "444b824c8b993ab9b8611686b5f199018ee879cc15b6c3ce6a34652747e55393",
        "scripts/engineering/__init__.py": "3e3e8f6480fb369be9a40fa9ba94c1242c95a2dd9206b38ab2920ddf44bddb88",
        "scripts/engineering/common/__init__.py": "b6de99ffe4e904b01bcd5d14fb8baf352c21ce16e7df6bd20ec72f0f606b2476",
        "scripts/engineering/repo/__init__.py": "b1466ec2a923038d19d5318b26af9938ab845aa91ce9623d016ab4feb7c15723",
        "scripts/engineering/dev/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "scripts/engineering/common/cli_dispatch.py": "ba6497eb3082cede709411e0a13c8fd13fc4b7f715a0d36f0f39b5a613af3f75",
        "scripts/engineering/common/repo_paths.py": "9a9c55bfbdcdd983e542594b8941e6ce7deda3a0afab1f887a42e3581ef2a4b9",
        "scripts/engineering/dev/run_project_python.py": "f471ba96238e014edfd7220daf6cfd53ea65efcb3e4fc03b506a7b94a085640d",
        "scripts/engineering/repo/__main__.py": "b3742415ad9389c86bfd01c08e33c7bd47438a750966f267aaafffb159a61b35",
        "scripts/engineering/repo/audit_root_cleanliness.py": "26b9951d197b059e307cd7d6b2e0eceacf1e350f70850abc13abd7d88bc5edca",
        "scripts/engineering/repo/_root_governance.py": "bb77f623d90875962f974668e2dc9ce8c98e92b7093d83b28611dc027ee3af66",
    }

    REVISIONS: ClassVar[dict[str, str]] = {
        "https://github.com/astral-sh/ruff-pre-commit": "v0.17.4",
        "https://github.com/pre-commit/pre-commit-hooks": "v6.0.0",
    }

    @classmethod
    def _digest(cls, entry: str, args: Any) -> str:
        return hashlib.sha256(
            json.dumps([*shlex.split(entry), *args], separators=(",", ":")).encode()
        ).hexdigest()

    @classmethod
    def _sources_match(cls, root: Path) -> bool:
        for relative, expected in cls.SOURCES.items():
            path = root / relative
            if (
                path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve())
                or path.stat().st_size > 256 * 1024
            ):
                return False
            if (
                hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                != expected
            ):
                return False
        return True

    @classmethod
    def qualified(
        cls, module: Any, config: Any, hooks: Any, skips: Any, args: Any, root: Path
    ) -> bool:
        if sys.platform != "linux" or args.hook_stage != "pre-commit" or skips:
            return False
        if config["fail_fast"] or args.fail_fast or any(h.fail_fast for h in hooks):
            return False
        try:
            classifier = module.Classifier.from_config(
                module._all_filenames(args), config["files"], config["exclude"]
            )
            active = [
                h
                for h in hooks
                if h.always_run or tuple(classifier.filenames_for_hook(h))
            ]
            if not active or len({h.id for h in active}) != len(active):
                return False
            for hook in active:
                if hook.log_file:
                    return False
                if cls.COMMANDS.get(hook.id) != (
                    hook.src,
                    hook.language,
                    cls._digest(hook.entry, hook.args),
                    hook.require_serial,
                ):
                    return False
                if hook.pass_filenames != (hook.id != "audit-root-cleanliness"):
                    return False
                if hook.src != "local":
                    repositories = [r for r in config["repos"] if r["repo"] == hook.src]
                    if (
                        len(repositories) != 1
                        or repositories[0].get("rev") != cls.REVISIONS[hook.src]
                    ):
                        return False
            return cls._sources_match(root)
        except (OSError, KeyError, ValueError, TypeError):
            return False

    @classmethod
    def _fresh_diff(
        cls,
    ) -> bytes:
        source = (
            Path(cls.__file__).resolve().parents[3]
            / "scripts/engineering/repo/hook_receipts.py"
        )
        spec = importlib.util.spec_from_file_location(
            "_bioetl_owned_partitioned", source
        )
        if spec is None or spec.loader is None:
            raise ValueError("partitioned_diff_unavailable")
        module = importlib.util.module_from_spec(spec)
        exec(compile(source.read_bytes(), str(source), "exec"), module.__dict__)
        return bytes(module._SourceDiffScanner.scan())

    @classmethod
    def dispatch(
        cls,
        module: Any,
        serial: Any,
        config: Any,
        hooks: Any,
        skips: Any,
        args: Any,
        *,
        root: Path,
        initial_clean: bool,
    ) -> int:
        if not initial_clean or not cls.qualified(
            module, config, hooks, skips, args, root
        ):
            return int(serial(config, hooks, skips, args))
        # The read-only staged context observed an empty diff before any callbacks.
        # Known formatters return nonzero on writes; validators are read-only.
        protocols = {
            (h.prefix.prefix_dir, h.entry, tuple(h.args), h.require_serial): h.src
            == "local"
            for h in hooks
            if cls.COMMANDS.get(h.id)
            == (h.src, h.language, cls._digest(h.entry, h.args), h.require_serial)
        }
        current = b""
        failed = False
        deferred = True

        def observe_diff() -> bytes:
            nonlocal current, deferred
            if failed:
                current = cls._fresh_diff()
                deferred = False
            return current

        def wrap(execute: Any) -> Any:
            def run(
                prefix: Any,
                entry: str,
                args: Any,
                filenames: Any,
                *,
                is_local: bool,
                require_serial: bool,
                color: bool,
            ) -> Any:
                nonlocal failed, deferred
                key = (prefix.prefix_dir, entry, tuple(args), require_serial)
                if key not in protocols or protocols[key] != is_local:
                    raise ValueError("coalesced_execution_contract_changed")
                code, output = execute(
                    prefix,
                    entry,
                    args,
                    filenames,
                    is_local=is_local,
                    require_serial=require_serial,
                    color=color,
                )
                failed = failed or bool(code)
                deferred = not failed
                return code, output

            return run

        with ExitStack() as stack:
            stack.enter_context(patch.object(module, "_get_diff", observe_diff))
            for name in {h.language for h in hooks}:
                language = module.languages[name]
                stack.enter_context(
                    patch.object(language, "run_hook", wrap(language.run_hook))
                )
            code = int(serial(config, hooks, skips, args))
        if deferred:
            # Always compare fresh source state after the last successful callback.
            # A command violating its declared behavior cannot yield a false PASS.
            code |= int(cls._fresh_diff() != b"")
        return code


if __name__ == "__main__":
    raise SystemExit(main())
