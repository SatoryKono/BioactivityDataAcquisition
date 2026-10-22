import os
import shlex
import subprocess
import sys
from typing import List

def run_sync(args: List[str]) -> None:
    # Whitelist of allowed flags for ci-control sync
    allowed_flags = {
        "sync",
        "--frozen",
        "--only-group",
        "ci-control",
    }

    parsed_args = []
    # Using POSIX shlex parsing
    try:
        # We join the arguments so shlex parses them properly based on quotes and spaces
        arg_string = " ".join(args)
        parsed_args = shlex.split(arg_string, posix=True)
    except ValueError as e:
        print(f"Error parsing arguments: {e}", file=sys.stderr)
        sys.exit(1)

    # Check for empty tokens that shlex might have preserved or stripped
    # Actually, empty strings are parsed as empty tokens by shlex, e.g. shlex.split("''") == [""]
    for arg in parsed_args:
        if "\0" in arg:
            print("Error: NUL character in arguments is not allowed.", file=sys.stderr)
            sys.exit(1)
        if not arg:
            print("Error: Empty string argument is not allowed.", file=sys.stderr)
            sys.exit(1)
        if arg.startswith("UV_"):
            print(f"Error: UV_* overrides like {arg} are not allowed.", file=sys.stderr)
            sys.exit(1)
        if arg not in allowed_flags:
            print(f"Error: Argument '{arg}' is not in the whitelist.", file=sys.stderr)
            sys.exit(1)

    if "--only-group" in parsed_args:
        group_idx = parsed_args.index("--only-group")
        if group_idx + 1 >= len(parsed_args) or parsed_args[group_idx + 1] != "ci-control":
             print("Error: --only-group must be followed by ci-control.", file=sys.stderr)
             sys.exit(1)

    command = ["uv"] + parsed_args
    print(f"Running securely: {' '.join(command)}")

    # Run securely without shell
    try:
        subprocess.run(command, check=True, shell=False)
    except subprocess.CalledProcessError as e:
        print(f"uv sync failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)

if __name__ == "__main__":
    run_sync(sys.argv[1:])
