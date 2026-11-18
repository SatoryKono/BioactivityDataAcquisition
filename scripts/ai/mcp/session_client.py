"""Select Memory/AST from the inherited native session cwd; never pin a cwd.

Run with the reviewed base interpreter and -I -S -B. This entrypoint accepts no
root override. The existing scoped Memory launcher still verifies identity and
the exact adapter process chain before HTTP requests.
"""

from __future__ import annotations

import argparse
import importlib.util
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
    if Path(sys.executable) != PYTHON or not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise PermissionError("Pinned isolated Python required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("memory", "ast-grep"))
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("session_workspace", HOST / "ast-workspace-profile.py")
    profiles = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profiles)
    root = session_root(Path.cwd(), profiles.physical_root)
    if args.service == "memory":
        command = [str(PYTHON), "-I", "-S", "-B", str(HOST / "project-memory-scoped-client.py"),
                   "--workspace", str(root), "--project", "BioETL", "--policy", "read-write"]
    else:
        command = [str(PYTHON), "-B", str(HOST / "codex-project-client.py"), "ast-grep"]
    return subprocess.call(command, creationflags=subprocess.CREATE_NO_WINDOW)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        sys.stderr.write("MCP session workspace verification failed; no fallback started.\n")
        raise SystemExit(64) from None
