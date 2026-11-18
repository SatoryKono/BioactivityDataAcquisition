"""Execute only the pinned read-only header checker in the owned project Python.

This is a semantic adapter for one known command, not arbitrary in-process hooks.
Unknown source/configuration/ownership retains ordinary framework execution.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import sys
from typing import Any
from unittest.mock import patch

# Source qualification pins; changes require fresh behavior qualification.
SOURCE_HASHES: dict[str, str] = {
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


def _digest(entry: str, args: Any) -> str:
    argv = [*shlex.split(entry), *args]
    return hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest()


def _sources_match(root: Path) -> bool:
    canonical = root.resolve()
    for name, expected in SOURCE_HASHES.items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(canonical):
            return False
        if not path.is_file() or path.stat().st_size > 256 * 1024:
            return False
        content = path.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() != expected:
            return False
    return True


def qualified(root: Path, hook_dir: Path) -> bool:
    """Require an owned bundle, exact sources and a sole read-only message hook."""
    try:
        if os.environ.get("SKIP") or not (root / "pyproject.toml").is_file():
            return False
        state_path = hook_dir / ".bioetl-hooks-state.json"
        if state_path.is_symlink() or state_path.stat().st_size > 128 * 1024:
            return False
        state = json.loads(state_path.read_bytes())
        bundle = Path(__file__).resolve().parents[3]
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
            "scripts/engineering/repo/readonly_message.py"
        ]
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != own_hash:
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
        if not _sources_match(root):
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
            hook["id"] == HOOK_ID
            and hook["language"] == "python"
            and hook.get("pass_filenames", True) is True
            and not hook.get("always_run", False)
            and not hook.get("alias", "")
            and not hook.get("files", "")
            and hook.get("exclude", "^$") == "^$"
            and _digest(hook["entry"], hook.get("args", ())) == COMMAND_HASH
        )
    except Exception:
        return False


def _invoke(root: Path, filename: str) -> tuple[int, bytes]:
    """Load the verified worktree packages, then restore only our namespaces."""
    path = Path(filename)
    metadata = Path(__file__).resolve().parents[3].parent.parent
    if (
        filename.startswith("-")
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(metadata)
    ):
        raise ValueError("message_input_outside_metadata")
    if not _sources_match(root):
        raise ValueError("message_sources_changed")
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name, _ in MODULES}
    search_path = sys.path[:]
    loaded = {}
    try:
        for name, relative in MODULES:
            path = root / relative
            locations = [str(path.parent)] if path.name == "__init__.py" else None
            spec = importlib.util.spec_from_file_location(
                name, path, submodule_search_locations=locations
            )
            if spec is None or spec.loader is None:
                raise ValueError("message_source_loader_unavailable")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
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
            [selected, "-m", "scripts.engineering.dev.check_commit_message", filename]
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


def dispatch(
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
        not qualified(root, hook_dir)
        or len(hooks) != 1
        or skips
        or args.hook_stage != "commit-msg"
    ):
        raise ValueError("message_contract_changed")
    hook = hooks[0]
    if (
        hook.id != HOOK_ID
        or hook.src != "local"
        or hook.language != "python"
        or not hook.pass_filenames
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
            or _digest(entry, args) != COMMAND_HASH
        ):
            raise ValueError("message_protocol_changed")
        called = True
        return _invoke(root, file_args[0])

    with (
        patch.object(language, "run_hook", execute),
        patch.object(module, "_get_diff", lambda: b""),
    ):
        code = int(serial(config, hooks, skips, args))
    if not called:
        raise ValueError("message_check_not_executed")
    return code
