"""Bounded Linux diff coalescing for checks that fail whenever they modify input.

Unknown active hooks/configuration/source retain ordinary per-hook diff checks.
This command adapter is not an OS sandbox or a cross-event evidence cache.
"""

from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any
from unittest.mock import patch

COMMANDS: dict[str, tuple[str, str, str, bool]] = {
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
SOURCES: dict[str, str] = {
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
REVISIONS = {
    "https://github.com/astral-sh/ruff-pre-commit": "v0.16.10",
    "https://github.com/pre-commit/pre-commit-hooks": "v6.0.0",
}


def _digest(entry: str, args: Any) -> str:
    return hashlib.sha256(
        json.dumps([*shlex.split(entry), *args], separators=(",", ":")).encode()
    ).hexdigest()


def _sources_match(root: Path) -> bool:
    for relative, expected in SOURCES.items():
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


def qualified(
    module: Any, config: Any, hooks: Any, skips: Any, args: Any, root: Path
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
            h for h in hooks if h.always_run or tuple(classifier.filenames_for_hook(h))
        ]
        if not active or len({h.id for h in active}) != len(active):
            return False
        for hook in active:
            if COMMANDS.get(hook.id) != (
                hook.src,
                hook.language,
                _digest(hook.entry, hook.args),
                hook.require_serial,
            ):
                return False
            if hook.pass_filenames != (hook.id != "audit-root-cleanliness"):
                return False
            if hook.src != "local":
                repositories = [r for r in config["repos"] if r["repo"] == hook.src]
                if (
                    len(repositories) != 1
                    or repositories[0].get("rev") != REVISIONS[hook.src]
                ):
                    return False
        return _sources_match(root)
    except (OSError, KeyError, ValueError, TypeError):
        return False


def _fresh_diff() -> bytes:
    # Unlike framework _get_diff(check=False), unavailable evidence is an error.
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.fsmonitor=false",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--ignore-submodules",
        ],
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"),
        capture_output=True,
        check=True,
        timeout=10,
    )
    return result.stdout


def dispatch(
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
    if not initial_clean or not qualified(module, config, hooks, skips, args, root):
        return int(serial(config, hooks, skips, args))
    # The read-only staged context observed an empty diff before any callbacks.
    # Known formatters return nonzero on writes; validators are read-only.
    protocols = {
        (h.prefix.prefix_dir, h.entry, tuple(h.args), h.require_serial): h.src
        == "local"
        for h in hooks
        if COMMANDS.get(h.id)
        == (h.src, h.language, _digest(h.entry, h.args), h.require_serial)
    }
    current = b""
    failed = False
    deferred = True

    def observe_diff() -> bytes:
        nonlocal current, deferred
        if failed:
            current = _fresh_diff()
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
        code |= int(_fresh_diff() != b"")
    return code
