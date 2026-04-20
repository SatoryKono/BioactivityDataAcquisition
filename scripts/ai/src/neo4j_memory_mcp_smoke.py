#!/usr/bin/env python3
"""Compatibility shim for the historical ``scripts.ai.src.neo4j_memory_mcp_smoke`` path."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.mcp.neo4j_memory_mcp_smoke import *  # noqa: F403
from scripts.ai.mcp.neo4j_memory_mcp_smoke import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(
            input=_build_handshake(),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke timed out before initialize/tools/list completed.",
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )

    try:
        responses = tuple(_parse_frames(stdout))
    except ValueError as exc:
        return SmokeResult(
            ok=False,
            summary=f"neo4j-memory MCP smoke received invalid framed output: {exc}",
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )

    initialize_response = _find_response(responses, _INITIALIZE_REQUEST_ID)
    tools_list_response = _find_response(responses, _TOOLS_LIST_REQUEST_ID)
    if initialize_response is None:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke did not receive an initialize response.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    if tools_list_response is None:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke did not receive a tools/list response.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    if "result" not in initialize_response:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP initialize response did not contain a result payload.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    if "result" not in tools_list_response:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP tools/list response did not contain a result payload.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    tools_payload = tools_list_response["result"]
    if not isinstance(tools_payload, dict) or "tools" not in tools_payload:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP tools/list response did not expose a tools array.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    if process.returncode != 0:
        return SmokeResult(
            ok=False,
            summary=(
                "neo4j-memory MCP smoke completed the handshake but the wrapper exited "
                f"with code {process.returncode}."
            ),
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    return SmokeResult(
        ok=True,
        summary=(
            "neo4j-memory MCP smoke completed initialize/tools/list over framed stdio."
        ),
        responses=responses,
        stderr=stderr.decode("utf-8", errors="replace"),
        returncode=process.returncode,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Smoke-check timeout in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--wrapper",
        nargs="+",
        default=_default_wrapper_command(),
        help=(
            "Wrapper command to execute. Defaults to the repo neo4j-memory wrapper. "
            "Pass a full command after --wrapper to override."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result = run_smoke_command(args.wrapper, timeout_seconds=args.timeout)
    stream = sys.stdout if result.ok else sys.stderr
    print(result.summary, file=stream)
    if result.stderr:
        print("Captured stderr:", file=stream)
        print(result.stderr.rstrip(), file=stream)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
