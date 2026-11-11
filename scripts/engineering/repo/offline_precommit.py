"""Qualified pre-commit 4.7.0 adapter: cached checks, never bootstrap on Git events.

This is a command wrapper, not a network or filesystem sandbox for hook code.
Explicit installation remains a separate operator action. Unknown framework
versions fail before any configured or legacy hook executes.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import closing, contextmanager
import importlib.metadata
import inspect
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any
from unittest.mock import patch

QUALIFIED_VERSION = "4.7.0"
HOOK_TYPES = frozenset({"pre-commit", "pre-push", "commit-msg"})


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


def _qualified_contract() -> bool:
    repository = importlib.import_module("pre_commit.repository")
    Store = importlib.import_module("pre_commit.store").Store

    expected = (
        (Store.__init__, ("self", "directory")),
        (Store._new_repo, ("self", "repo", "ref", "deps", "make_strategy")),
        (repository.install_hook_envs, ("hooks", "store")),
        (repository._hook_install, ("hook",)),
        (repository._hook_installed, ("hook",)),
        (importlib.import_module("pre_commit.error_handler").error_handler, ()),
    )
    return all(
        tuple(inspect.signature(fn).parameters) == names for fn, names in expected
    )


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

            with (
                patch.object(run_module, "install_hook_envs", _require_environments),
                patch.object(framework_main, "error_handler", _quiet_errors),
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
