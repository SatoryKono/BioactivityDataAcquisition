"""Allow only the frozen ci-control uv sync command.

The composite action calls this wrapper with a fixed argument vector. Tokens
are not joined or parsed with shlex, so one argument cannot split into extra
uv flags.
"""

from __future__ import annotations

import os
import subprocess
import sys

_ALLOWED_ARGV = ("sync", "--frozen", "--only-group", "ci-control")
# UV_PYTHON is pinned by the action. UV_CACHE_DIR is exported by setup-uv.
_ALLOWED_UV_ENV = frozenset({"UV_CACHE_DIR", "UV_PYTHON"})


def run_sync(args: list[str]) -> None:
    """Execute ``uv sync --frozen --only-group ci-control`` or exit."""
    for arg in args:
        if "\0" in arg:
            print(
                "Error: NUL character in arguments is not allowed.",
                file=sys.stderr,
            )
            sys.exit(1)
        if arg == "":
            print("Error: Empty string argument is not allowed.", file=sys.stderr)
            sys.exit(1)
        if arg.startswith("UV_"):
            print(
                f"Error: UV_* overrides like {arg} are not allowed.",
                file=sys.stderr,
            )
            sys.exit(1)

    if tuple(args) != _ALLOWED_ARGV:
        print(
            "Error: Argument list is not in the whitelist "
            "(sync --frozen --only-group ci-control).",
            file=sys.stderr,
        )
        sys.exit(1)

    blocked = sorted(
        key
        for key in os.environ
        if key.startswith("UV_") and key not in _ALLOWED_UV_ENV
    )
    if blocked:
        print(
            "Error: UV_* overrides are not allowed: " + ", ".join(blocked),
            file=sys.stderr,
        )
        sys.exit(1)

    command = ["uv", *_ALLOWED_ARGV]
    print("Running securely: " + " ".join(command))
    try:
        subprocess.run(command, check=True, shell=False)
    except subprocess.CalledProcessError as exc:
        print(
            f"uv sync failed with exit code {exc.returncode}",
            file=sys.stderr,
        )
        sys.exit(exc.returncode)


if __name__ == "__main__":
    run_sync(sys.argv[1:])
