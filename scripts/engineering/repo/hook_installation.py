"""Install, inspect and roll back owned Git hooks without changing Git settings.

Deployment copies are immutable helper bundles, never partial Git checkouts.
The installer does not execute callbacks, install dependencies or touch env files.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Any, ClassVar
from unittest.mock import patch

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
    "hook_receipts",
)
STATE = ".bioetl-hooks-state.json"
MANIFEST = "manifest.json"
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
        if _hash(_read(bundle / MANIFEST)) != state["manifest_sha256"]:
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
    manifest = json.loads(_read(bundle / MANIFEST))
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
    (destination / MANIFEST).write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    return destination, sha


def _launcher(bundle: Path, interpreter: Path, name: str, hooks: Path) -> bytes:
    # -I excludes cwd/PYTHONPATH. The digest is embedded independently of manifest.
    manifest_hash = _hash(_read(bundle / MANIFEST))
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


def _existing_installation(
    repo: Path,
    hooks: Path,
    requested_sha: str,
    interpreter: Path,
    requested_cache: Path,
) -> dict[str, Any] | None:
    if (hooks / STATE).is_symlink():
        raise ValueError("symlink state requires host review")
    if (hooks / STATE).exists():
        result = inspect_installation(repo)
        if result["status"] != "PASS":
            raise ValueError("existing owned installation changed; refuse overwrite")
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
    return None


def _callback_record(
    hooks: Path,
    bundle: Path,
    interpreter: Path,
    name: str,
    original: tuple[bytes, int] | None,
) -> dict[str, Any]:
    content = _launcher(bundle, interpreter, name, hooks)
    backup = None
    if original is not None:
        backup = name + ".bioetl-previous-" + _hash(original[0])
        if (hooks / backup).is_symlink():
            raise ValueError("symlink backup requires host review")
        if (hooks / backup).exists() and _read(hooks / backup) != original[0]:
            raise ValueError("foreign backup collision")
    framework_owned = (
        original is not None and b"# File generated by pre-commit:" in original[0]
    )
    return {
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


def _prepare_callbacks(
    hooks: Path,
    bundle: Path,
    interpreter: Path,
    state: dict[str, Any],
) -> dict[str, tuple[bytes, int] | None]:
    originals: dict[str, tuple[bytes, int] | None] = {}
    for name in HOOKS:
        path = hooks / name
        if path.is_symlink():
            raise ValueError("symlink callback requires host review")
        originals[name] = (_read(path), path.stat().st_mode) if path.exists() else None
        state["hooks"][name] = _callback_record(
            hooks, bundle, interpreter, name, originals[name]
        )
    return originals


def _apply_callbacks(
    hooks: Path,
    bundle: Path,
    interpreter: Path,
    state: dict[str, Any],
    originals: dict[str, tuple[bytes, int] | None],
) -> None:
    try:
        for name, original in originals.items():
            if original is not None:
                backup_path = hooks / state["hooks"][name]["backup"]
                _atomic_write(backup_path, original[0], original[1])
            target = hooks / name
            _atomic_write(target, _launcher(bundle, interpreter, name, hooks), 0o755)
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
        existing = _existing_installation(
            repo, hooks, requested_sha, interpreter, requested_cache
        )
        if existing is not None:
            return existing
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
            "manifest_sha256": _hash(_read(bundle / MANIFEST)),
        }
        originals = _prepare_callbacks(hooks, bundle, interpreter, state)
        _apply_callbacks(hooks, bundle, interpreter, state, originals)
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


class _ReadOnlyMessage:
    """Execute only the pinned read-only header checker in the owned project Python."""

    __file__ = __file__

    SOURCE_HASHES: ClassVar[dict[str, str]] = {
        "scripts/__init__.py": "444b824c8b993ab9b8611686b5f199018ee879cc15b6c3ce6a34652747e55393",
        "scripts/engineering/__init__.py": "3e3e8f6480fb369be9a40fa9ba94c1242c95a2dd9206b38ab2920ddf44bddb88",
        "scripts/engineering/common/__init__.py": "b6de99ffe4e904b01bcd5d14fb8baf352c21ce16e7df6bd20ec72f0f606b2476",
        "scripts/engineering/dev/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "scripts/engineering/common/repo_paths.py": "9a9c55bfbdcdd983e542594b8941e6ce7deda3a0afab1f887a42e3581ef2a4b9",
        "scripts/engineering/dev/run_project_python.py": "f471ba96238e014edfd7220daf6cfd53ea65efcb3e4fc03b506a7b94a085640d",
        "scripts/engineering/dev/check_commit_message.py": "070c7d1197852a7dd653f564dc544b910cd504af8056e5266f777f440413fc2e",
    }

    COMMAND_HASH = "48c03bd8f4cf83b36a00272ed63d0b4640fa589b7256f6bbae21bf825986e152"

    HOOK_ID = "commit-message-conventional"

    MODULES = (
        ("scripts", "scripts/__init__.py"),
        ("scripts.engineering", "scripts/engineering/__init__.py"),
        ("scripts.engineering.common", "scripts/engineering/common/__init__.py"),
        ("scripts.engineering.dev", "scripts/engineering/dev/__init__.py"),
        (
            "scripts.engineering.common.repo_paths",
            "scripts/engineering/common/repo_paths.py",
        ),
        (
            "scripts.engineering.dev.run_project_python",
            "scripts/engineering/dev/run_project_python.py",
        ),
        (
            "scripts.engineering.dev.check_commit_message",
            "scripts/engineering/dev/check_commit_message.py",
        ),
    )

    @classmethod
    def _digest(cls, entry: str, args: Any) -> str:
        argv = [*shlex.split(entry), *args]
        return hashlib.sha256(
            json.dumps(argv, separators=(",", ":")).encode()
        ).hexdigest()

    @classmethod
    def _sources_match(cls, root: Path) -> bool:
        canonical = root.resolve()
        for name, expected in cls.SOURCE_HASHES.items():
            path = root / name
            if path.is_symlink() or not path.resolve().is_relative_to(canonical):
                return False
            if not path.is_file() or path.stat().st_size > 256 * 1024:
                return False
            content = path.read_bytes().replace(b"\r\n", b"\n")
            if hashlib.sha256(content).hexdigest() != expected:
                return False
        return True

    @classmethod
    def qualified(cls, root: Path, hook_dir: Path) -> bool:
        """Require an owned bundle, exact sources and a sole read-only message hook."""
        try:
            if os.environ.get("SKIP") or not (root / "pyproject.toml").is_file():
                return False
            state_path = hook_dir / ".bioetl-hooks-state.json"
            if state_path.is_symlink() or state_path.stat().st_size > 128 * 1024:
                return False
            state = json.loads(state_path.read_bytes())
            bundle = Path(cls.__file__).resolve().parents[3]
            if (
                Path(state["bundle"]).resolve() != bundle
                or type(state["version"]) is not int
                or state["version"] != 1
            ):
                return False
            if (
                bundle.parent.name != "bioetl-hooks"
                or not hook_dir.resolve().is_relative_to(bundle.parent.parent)
            ):
                return False
            manifest = (bundle / "manifest.json").read_bytes()
            if hashlib.sha256(manifest).hexdigest() != state["manifest_sha256"]:
                return False
            own_hash = json.loads(manifest)["files"][
                "scripts/engineering/repo/hook_installation.py"
            ]
            if hashlib.sha256(Path(cls.__file__).read_bytes()).hexdigest() != own_hash:
                return False

            def normalize(value: str) -> str:
                return os.path.normcase(os.path.abspath(value))

            if normalize(state["python"]) != normalize(sys.executable):
                return False
            if normalize(os.environ.get("BIOETL_HOOK_PROJECT_PYTHON", "")) != normalize(
                sys.executable
            ):
                return False
            for kind in ("pre-commit", "pre-push", "commit-msg"):
                if state["hooks"][kind]["chain_foreign"] is not False:
                    return False
                if os.path.lexists(hook_dir / (kind + ".legacy")):
                    return False
            if not cls._sources_match(root):
                return False
            from pre_commit.clientlib import load_config

            config = load_config(str(root / ".pre-commit-config.yaml"))
            if config["files"] != "" or config["exclude"] != "^$":
                return False
            messages = []
            for repo in config["repos"]:
                for hook in repo["hooks"]:
                    if "stages" not in hook:
                        return False
                    if "commit-msg" in hook["stages"]:
                        if repo["repo"] != "local":
                            return False
                        messages.append(hook)
            if len(messages) != 1:
                return False
            hook = messages[0]
            return (
                hook["id"] == cls.HOOK_ID
                and hook["language"] == "python"
                and hook.get("pass_filenames", True) is True
                and not hook.get("always_run", False)
                and not hook.get("log_file")
                and not hook.get("alias", "")
                and not hook.get("files", "")
                and hook.get("exclude", "^$") == "^$"
                and hook.get("types", ["file"]) == ["file"]
                and hook.get("types_or", []) == []
                and hook.get("exclude_types", []) == []
                and cls._digest(hook["entry"], hook.get("args", ())) == cls.COMMAND_HASH
            )
        except Exception:
            return False

    @classmethod
    def _invoke(cls, root: Path, filename: str) -> tuple[int, bytes]:
        """Load the verified worktree packages, then restore only our namespaces."""
        path = Path(filename)
        metadata = Path(cls.__file__).resolve().parents[3].parent.parent
        if (
            filename.startswith("-")
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(metadata)
        ):
            raise ValueError("message_input_outside_metadata")
        if not cls._sources_match(root):
            raise ValueError("message_sources_changed")
        missing = object()
        previous = {name: sys.modules.get(name, missing) for name, _ in cls.MODULES}
        search_path = sys.path[:]
        loaded = {}
        try:
            for name, relative in cls.MODULES:
                path = root / relative
                locations = [str(path.parent)] if path.name == "__init__.py" else None
                spec = importlib.util.spec_from_file_location(
                    name, path, submodule_search_locations=locations
                )
                if spec is None or spec.loader is None:
                    raise ValueError("message_source_loader_unavailable")
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                content = path.read_bytes()
                if (
                    hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()
                    != cls.SOURCE_HASHES[relative]
                ):
                    raise ValueError("message_sources_changed")
                # Execute exactly the bytes just qualified, never a stale .pyc.
                exec(compile(content, str(path), "exec"), module.__dict__)
                loaded[name] = module
                if "." in name:
                    parent, attr = name.rsplit(".", 1)
                    setattr(loaded[parent], attr, module)
            runner = loaded["scripts.engineering.dev.run_project_python"]
            selected = runner._preferred_python()
            if os.path.normcase(os.path.abspath(selected)) != os.path.normcase(
                os.path.abspath(sys.executable)
            ):
                raise ValueError("message_project_interpreter_changed")
            runner.ensure_safe_cli_argv(
                [
                    selected,
                    "-m",
                    "scripts.engineering.dev.check_commit_message",
                    filename,
                ]
            )
            output, error = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                code = loaded["scripts.engineering.dev.check_commit_message"].main(
                    [filename]
                )
            return int(code), (output.getvalue() + error.getvalue()).encode()
        finally:
            for name, value in previous.items():
                if value is missing:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value
            sys.path[:] = search_path

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
        hook_dir: Path,
    ) -> int:
        """Keep framework filtering/statuses; the known checker never writes source."""
        if (
            not cls.qualified(root, hook_dir)
            or len(hooks) != 1
            or skips
            or args.hook_stage != "commit-msg"
        ):
            raise ValueError("message_contract_changed")
        hook = hooks[0]
        if (
            hook.id != cls.HOOK_ID
            or hook.src != "local"
            or hook.language != "python"
            or not hook.pass_filenames
            or bool(hook.log_file)
        ):
            raise ValueError("message_hook_changed")
        language = module.languages["python"]
        called = False
        expected_options = (hook.require_serial, args.color)

        def execute(
            prefix: Any,
            entry: str,
            args: Any,
            file_args: Any,
            *,
            is_local: bool,
            require_serial: bool,
            color: bool,
        ) -> tuple[int, bytes]:
            nonlocal called
            if (
                called
                or (require_serial, color) != expected_options
                or not is_local
                or prefix != hook.prefix
                or len(file_args) != 1
                or cls._digest(entry, args) != cls.COMMAND_HASH
            ):
                raise ValueError("message_protocol_changed")
            called = True
            return cls._invoke(root, file_args[0])

        with (
            patch.object(language, "run_hook", execute),
            patch.object(module, "_get_diff", lambda: b""),
        ):
            code = int(serial(config, hooks, skips, args))
        if not called:
            raise ValueError("message_check_not_executed")
        return code


if __name__ == "__main__":
    raise SystemExit(main())
