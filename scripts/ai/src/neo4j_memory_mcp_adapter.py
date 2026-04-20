#!/usr/bin/env python3
"""Compatibility shim for the historical ``scripts.ai.src.neo4j_memory_mcp_adapter`` path."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.mcp.neo4j_memory_mcp_adapter import *  # noqa: F403
from scripts.ai.mcp.neo4j_memory_mcp_adapter import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


def _pump_stderr(source: BinaryIO, target: BinaryIO) -> None:
    for chunk in iter(lambda: source.readline(), b""):
        target.write(chunk)
        target.flush()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Inner server command, introduced by --.",
    )
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("Missing inner server command. Pass it after --.")
    args.command = command
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    process = subprocess.Popen(
        list(args.command),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    errors: Queue[PumpError] = Queue()
    threads = [
        threading.Thread(
            target=_pump_framed_to_line,
            kwargs={
                "source": sys.stdin.buffer,
                "target": process.stdin,
                "errors": errors,
            },
            daemon=True,
        ),
        threading.Thread(
            target=_pump_line_to_framed,
            kwargs={
                "source": process.stdout,
                "target": sys.stdout.buffer,
                "errors": errors,
            },
            daemon=True,
        ),
        threading.Thread(
            target=_pump_stderr,
            kwargs={"source": process.stderr, "target": sys.stderr.buffer},
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    returncode = process.wait()
    for thread in threads:
        thread.join(timeout=1.0)

    if not errors.empty():
        error = errors.get()
        print(
            f"neo4j-memory MCP adapter error on {error.source}: {error.message}",
            file=sys.stderr,
        )
        return 1
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
