"""Install, inspect and roll back owned Git hooks without changing Git settings.

Deployment copies are immutable helper bundles, never partial Git checkouts.
The installer does not execute callbacks, install dependencies or touch env files.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Any

HOOKS = ("pre-commit", "pre-push", "commit-msg")
MODULES = (
    "operation_guards",
    "budget_guard",
    "check_no_partial_tree",
    "process_deadline",
    "process_supervisor",
    "offline_precommit",
    "hook_runtime",
    "hook_installation",
)
STATE = ".bioetl-hooks-state.json"
MAX_BYTES = 2 * 1024 * 1024


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repo: Path, *args: str, strip: bool = True) -> str:
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(name, None)
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        timeout=10,
        check=True,
    )
    if len(result.stdout) > MAX_BYTES:
        raise ValueError("git evidence too large")
    decoded = result.stdout.decode("utf-8")
    return decoded.strip() if strip else decoded


def locations(repo: Path) -> tuple[Path, Path]:
    """Read effective config; an unsupported external hooks directory is an error."""
    common = Path(
        _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    ).resolve()
    hooks = Path(
        _git(repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks")
    )
    if hooks.is_symlink():
        raise ValueError("symlink hooks directory requires host review")
    hooks = hooks.resolve()
    if not hooks.is_relative_to(common):
        raise ValueError("external core.hooksPath requires host review")
    return common, hooks


def _read(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError("symlink state or callback requires host review")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("file exceeds evidence limit")
    return data


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    """Git readers see an entire callback, never a half-written shell script."""
    descriptor, raw = tempfile.mkstemp(prefix=".bioetl-hook-", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _lock(hooks: Path) -> Iterator[None]:
    lock = hooks / ".bioetl-hooks.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        yield
    finally:
        os.close(descriptor)
        lock.unlink()


def _state(hooks: Path) -> dict[str, Any]:
    data = json.loads(_read(hooks / STATE))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("unknown installation state")
    if set(data.get("hooks", {})) != set(HOOKS):
        raise ValueError("incomplete installation state")
    for name, item in data["hooks"].items():
        if not isinstance(item, dict):
            raise ValueError("invalid callback state")
        backup = item.get("backup")
        if backup is not None and backup != name + ".bioetl-previous-" + str(
            item.get("backup_sha256")
        ):
            raise ValueError("invalid backup identity")
    return data


def inspect_installation(repo: Path) -> dict[str, Any]:
    """Presence qualifies only with effective location and matching owned bytes."""
    try:
        _, hooks = locations(repo)
        state = _state(hooks)
        for name in HOOKS:
            if _hash(_read(hooks / name)) != state["hooks"][name]["installed_sha256"]:
                raise ValueError("owned hook changed")
            if os.name != "nt" and not os.access(hooks / name, os.X_OK):
                raise ValueError("owned hook is not executable")
        bundle = Path(state["bundle"])
        if _hash(_read(bundle / "manifest.json")) != state["manifest_sha256"]:
            raise ValueError("bundle manifest changed")
        verify_bundle(bundle)
        if not Path(state["python"]).is_file():
            raise ValueError("installed interpreter unavailable")
        return {
            "status": "PASS",
            "source_sha": state["source_sha"],
            "hooks": list(HOOKS),
            "effective_hooks_path": str(hooks),
            "bundle": str(bundle),
            "interpreter": state["python"],
            "pre_commit_home": str(_cache_directory(Path(state["pre_commit_home"]))),
            "route": "protected_guards -> preserved_foreign -> cached_pre_commit",
            "execution_status": "NOT_TESTED",
        }
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        subprocess.SubprocessError,
    ):
        return {"status": "ERROR", "reason": "installation_not_qualified"}


def verify_bundle(bundle: Path) -> None:
    manifest = json.loads(_read(bundle / "manifest.json"))
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise ValueError("unknown bundle manifest")
    for relative, digest in manifest["files"].items():
        path = bundle / relative
        if not path.resolve().is_relative_to(bundle.resolve()):
            raise ValueError("bundle path escaped")
        if _hash(_read(path)) != digest:
            raise ValueError("bundle changed")


def _source_sha(repo: Path, source: str) -> str:
    sha = _git(repo, "rev-parse", "--verify", "--end-of-options", source + "^{commit}")
    if len(sha) not in {40, 64} or any(
        character not in "0123456789abcdef" for character in sha
    ):
        raise ValueError("invalid source identity")
    return sha


def _bundle(repo: Path, common: Path, source: str) -> tuple[Path, str]:
    sha = _source_sha(repo, source)
    files: dict[str, bytes] = {}
    for module in MODULES:
        path = f"scripts/engineering/repo/{module}.py"
        files[path] = _git(repo, "show", f"{sha}:{path}", strip=False).encode("utf-8")
    for package in ("scripts", "scripts/engineering", "scripts/engineering/repo"):
        files[package + "/__init__.py"] = b""
    fingerprint = _hash(
        b"".join(name.encode() + b"\0" + value for name, value in sorted(files.items()))
    )
    destination = common / "bioetl-hooks" / fingerprint
    if destination.exists():
        verify_bundle(destination)
        return destination, sha
    destination.mkdir(parents=True)
    for name, content in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    manifest = {
        "version": 1,
        "files": {name: _hash(value) for name, value in files.items()},
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    return destination, sha


def _launcher(bundle: Path, interpreter: Path, name: str, hooks: Path) -> bytes:
    # -I excludes cwd/PYTHONPATH. The digest is embedded independently of manifest.
    manifest_hash = _hash(_read(bundle / "manifest.json"))
    bootstrap = (
        "import hashlib,json,pathlib,runpy,sys;"
        f"p=pathlib.Path({str(bundle)!r});"
        "m=(p/'manifest.json').read_bytes();"
        f"assert hashlib.sha256(m).hexdigest()=={manifest_hash!r};"
        "d=json.loads(m);"
        "assert all((p/k).resolve().is_relative_to(p.resolve()) and "
        "hashlib.sha256((p/k).read_bytes()).hexdigest()==v for k,v in d['files'].items());"
        "sys.path.insert(0,str(p));"
        "runpy.run_module('scripts.engineering.repo.hook_runtime',run_name='__main__')"
    )
    command = [
        str(interpreter).replace("\\", "/"),
        "-I",
        "-B",
        "-c",
        bootstrap,
        name,
        str(hooks),
    ]
    return (
        "#!/bin/sh\n# BioETL managed hook v1\nexec "
        + " ".join(shlex.quote(x) for x in command)
        + ' "$@"\n'
    ).encode()


def _cache_directory(explicit: Path | None = None) -> Path:
    """Pin pre-commit 4.7.0's cache selection without constructing its Store."""
    if explicit is None:
        raw = os.environ.get("PRE_COMMIT_HOME")
        cache = (
            Path(raw)
            if raw
            else Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
            / "pre-commit"
        )
    else:
        cache = explicit
    if not cache.is_absolute():
        raise ValueError("absolute pre-commit cache required")
    return cache.resolve()


def install(
    repo: Path,
    interpreter: Path,
    source: str = "origin/main",
    *,
    pre_commit_home: Path | None = None,
) -> dict[str, Any]:
    """One locked transaction; foreign callbacks remain byte-for-byte recoverable."""
    common, hooks = locations(repo)
    requested_cache = _cache_directory(pre_commit_home)
    if not interpreter.is_absolute() or not interpreter.is_file():
        raise ValueError("explicit absolute project interpreter required")
    hooks.mkdir(parents=True, exist_ok=True)
    with _lock(hooks):
        requested_sha = _source_sha(repo, source)
        if (hooks / STATE).is_symlink():
            raise ValueError("symlink state requires host review")
        if (hooks / STATE).exists():
            result = inspect_installation(repo)
            if result["status"] != "PASS":
                raise ValueError(
                    "existing owned installation changed; refuse overwrite"
                )
            installed_python = os.path.normcase(os.path.abspath(result["interpreter"]))
            requested_python = os.path.normcase(os.path.abspath(interpreter))
            if (
                result["source_sha"] != requested_sha
                or installed_python != requested_python
                or result["pre_commit_home"] != str(requested_cache)
            ):
                return {
                    "status": "ERROR",
                    "reason": "explicit_upgrade_required",
                    "installed_source_sha": result["source_sha"],
                    "requested_source_sha": requested_sha,
                    "next_step": "Inspect hooks doctor, then explicitly rollback and reinstall.",
                }
            return result
        bundle, sha = _bundle(repo, common, requested_sha)
        if sha != requested_sha:
            raise ValueError("source identity changed during bundle creation")
        state: dict[str, Any] = {
            "version": 1,
            "bundle": str(bundle),
            "python": str(interpreter),
            "pre_commit_home": str(requested_cache),
            "source_sha": sha,
            "hooks": {},
            "manifest_sha256": _hash(_read(bundle / "manifest.json")),
        }
        originals: dict[str, tuple[bytes, int] | None] = {}
        for name in HOOKS:
            path = hooks / name
            if path.is_symlink():
                raise ValueError("symlink callback requires host review")
            originals[name] = (
                (_read(path), path.stat().st_mode) if path.exists() else None
            )
            content = _launcher(bundle, interpreter, name, hooks)
            original = originals[name]
            backup = None
            if original is not None:
                backup = name + ".bioetl-previous-" + _hash(original[0])
                if (hooks / backup).is_symlink():
                    raise ValueError("symlink backup requires host review")
                if (hooks / backup).exists() and _read(hooks / backup) != original[0]:
                    raise ValueError("foreign backup collision")
            framework_owned = (
                original is not None
                and b"# File generated by pre-commit:" in original[0]
            )
            state["hooks"][name] = {
                "installed_sha256": _hash(content),
                "backup": backup,
                "backup_sha256": _hash(original[0]) if original else None,
                "mode": original[1] if original else None,
                "chain_foreign": bool(
                    original
                    and not framework_owned
                    and (os.name == "nt" or original[1] & 0o111)
                ),
            }
        try:
            for name, original in originals.items():
                if original is not None:
                    backup_path = hooks / state["hooks"][name]["backup"]
                    _atomic_write(backup_path, original[0], original[1])
                target = hooks / name
                _atomic_write(
                    target, _launcher(bundle, interpreter, name, hooks), 0o755
                )
            _atomic_write(
                hooks / STATE, json.dumps(state, sort_keys=True).encode("utf-8"), 0o600
            )
        except BaseException:
            for name, original in originals.items():
                target = hooks / name
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    _atomic_write(target, original[0], original[1])
            (hooks / STATE).unlink(missing_ok=True)
            raise
        return inspect_installation(repo)


def rollback(repo: Path) -> None:
    _, hooks = locations(repo)
    with _lock(hooks):
        state = _state(hooks)
        # Validate all before mutating any. Never overwrite a later owner's edit.
        for name, item in state["hooks"].items():
            if _hash(_read(hooks / name)) != item["installed_sha256"]:
                raise ValueError("owned hook changed")
            if (
                item["backup"]
                and _hash(_read(hooks / item["backup"])) != item["backup_sha256"]
            ):
                raise ValueError("foreign backup changed")
        for name, item in state["hooks"].items():
            target = hooks / name
            if item["backup"]:
                _atomic_write(target, _read(hooks / item["backup"]), item["mode"])
            else:
                target.unlink()
        (hooks / STATE).unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "doctor", "rollback"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--python", type=Path)
    parser.add_argument("--source", default="origin/main")
    parser.add_argument("--pre-commit-home", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "doctor":
            result = inspect_installation(args.repo)
        elif args.action == "rollback":
            rollback(args.repo)
            result = {"status": "PASS", "action": "rollback"}
        else:
            if args.python is None:
                raise ValueError("explicit interpreter required")
            result = install(
                args.repo,
                args.python,
                args.source,
                pre_commit_home=args.pre_commit_home,
            )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        subprocess.SubprocessError,
    ):
        result = {
            "status": "ERROR",
            "reason": "installation_evidence_or_ownership_unavailable",
        }
    print(json.dumps(result))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
