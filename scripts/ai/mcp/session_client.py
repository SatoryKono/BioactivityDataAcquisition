"""Select Memory/AST from the inherited native session cwd; never pin a cwd.

Run with the reviewed base interpreter and -I -S -B. This entrypoint accepts no
root override. The existing scoped Memory launcher still verifies identity and
the exact adapter process chain before HTTP requests.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HOST = Path("D:/pc-agent/tools/shared-mcp")
PYTHON = Path("C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe")


def session_root(cwd: Path, validator) -> Path:
    """The nearest Git marker is authoritative, including nested repositories."""
    if not cwd.is_absolute() or cwd.resolve(strict=True) != cwd:
        raise PermissionError("Session cwd is not physical")
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return validator(candidate)
    raise PermissionError("No registered session workspace")


def main() -> int:
    if Path(sys.executable) != PYTHON or not (
        sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    ):
        raise PermissionError("Pinned isolated Python required")
    manifest_path = Path(__file__).with_name("dispatcher.json")
    if manifest_path.is_file():
        raw = manifest_path.read_bytes()
        directory = manifest_path.parent
        manifest = json.loads(raw)
        if (
            hashlib.sha256(raw).hexdigest() != directory.name
            or manifest.get("schema") != 1
        ):
            raise PermissionError("Session dispatcher identity changed")
        for relative, expected in manifest["files"].items():
            path = directory / relative
            if (
                Path(relative).is_absolute()
                or ".." in Path(relative).parts
                or path.resolve(strict=True) != path
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                raise PermissionError("Session dispatcher source changed")
        for path, expected in manifest["host_pins"].items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
                raise PermissionError("Session dispatcher host dependency changed")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("memory", "memory-acceptance", "ast-grep"))
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "session_workspace", HOST / "ast-workspace-profile.py"
    )
    profiles = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profiles)
    root = session_root(Path.cwd(), profiles.physical_root)
    if args.service in {"memory", "memory-acceptance"}:
        scope_spec = importlib.util.spec_from_file_location(
            "session_memory_scope", HOST / "project-memory-scope.py"
        )
        scope = importlib.util.module_from_spec(scope_spec)
        scope_spec.loader.exec_module(scope)
        context = scope.git_context(root)
        project = (
            "BioETL-Acceptance-Test"
            if args.service == "memory-acceptance"
            else "BioETL"
        )
        identity = scope.describe(
            root, project=project, branch=context["branch"], policy="read-write"
        )["id"]
        version_spec = importlib.util.spec_from_file_location(
            "session_memory_versions", Path(__file__).with_name("memory_versions.py")
        )
        versions = importlib.util.module_from_spec(version_spec)
        version_spec.loader.exec_module(versions)
        private = Path.home() / "AppData/Local/pc-agent/mcp-shared/project-memory-v1"
        bundle = versions.select_bundle(private, identity)
        runtime = bundle / "tools/shared-mcp" if bundle else HOST
        python = bundle / "runtime/python/python.exe" if bundle else PYTHON
        command = [
            str(python),
            "-I",
            "-S",
            "-B",
            str(runtime / "project-memory-scoped-client.py"),
            "--workspace",
            str(root),
            "--project",
            project,
            "--policy",
            "read-write",
        ]
    else:
        command = [str(PYTHON), "-B", str(HOST / "codex-project-client.py"), "ast-grep"]
    core_spec = importlib.util.spec_from_file_location(
        "session_owner_primitives", HOST / "supervisor.py"
    )
    core = importlib.util.module_from_spec(core_spec)
    core_spec.loader.exec_module(core)
    job = core.Job()
    child = None
    attached = False
    try:
        child = subprocess.Popen(
            command,
            stdin=sys.stdin.buffer,
            stdout=sys.stdout.buffer,
            stderr=sys.stderr.buffer,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        job.attach(child)
        attached = True
        return child.wait()
    finally:
        job.close()
        if child is not None and child.poll() is None:
            if not attached:
                child.terminate()
            child.wait(timeout=10)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        sys.stderr.write(
            "MCP session workspace verification failed; no fallback started.\n"
        )
        raise SystemExit(64) from None
