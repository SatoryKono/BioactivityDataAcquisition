#!/usr/bin/env python3
"""Static and bounded live diagnostics for the BioETL Codex runtime."""

from __future__ import annotations

import argparse
import queue
import json
import shutil
import socket
import time
import threading
import urllib.request
from pathlib import Path
from typing import Any, cast
import sys

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import setup_mcp  # pyright: ignore[reportImplicitRelativeImport]
from mcp_profile_contract import (
    effective_profile_plan,
    profile_plan,
    validate_profile_matrix,
)  # pyright: ignore[reportImplicitRelativeImport]
from native_runtime_contract import Finding, REPO_ROOT, validate_native_runtime  # pyright: ignore[reportImplicitRelativeImport]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.sync.governance import normalize_codex_agents


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return []


WINDOWS_STREAMING_MODES = {"windows_docker_streaming", "windows_npx_streaming"}
DAILY_PROFILES = {"stable", "shared"}


def run_static(repo_root: Path, *, output_json: bool = False) -> int:
    findings = validate_native_runtime(repo_root)
    findings.extend(
        Finding(
            "governance.normalization",
            issue,
            issue.split(":", 1)[0],
        )
        for issue in normalize_codex_agents(repo_root, check_only=True)
    )
    findings.extend(
        Finding("mcp.matrix", error, "scripts/ai/codex/setup_mcp.py")
        for error in validate_profile_matrix(repo_root)
    )
    if output_json:
        print(
            json.dumps(
                {"ok": not findings, "findings": [item.as_dict() for item in findings]},
                indent=2,
            )
        )
    else:
        for finding in findings:
            print(f"[FAIL] {finding.code}: {finding.message} ({finding.path})")
        if not findings:
            print(
                "[OK] native project config, agents, skills, and MCP matrices are valid"
            )
    return 1 if findings else 0


def _probe(name: str, entry: dict[str, Any], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + timeout
    port = int(entry["port"])
    path = str(entry.get("path") or "/mcp")
    url = f"http://127.0.0.1:{port}{path}"
    port_open = False
    ping_ok = False
    detail = "connection refused or timed out"
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            port_open = True
        if entry.get("launch_mode") in WINDOWS_STREAMING_MODES:
            ping_ok = True
            detail = "listener ready; streaming bridge has no /ping requirement"
        else:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/ping",
                timeout=max(0.001, deadline - time.monotonic()),
            ) as response:
                ping_ok = 200 <= response.status < 500
                detail = f"/ping HTTP {response.status}"
    except Exception as exc:  # bounded diagnostic reports endpoint-level cause
        detail = f"{type(exc).__name__}: {exc}"
    return {
        "server": name,
        "url": url,
        "port_open": port_open,
        "ping_ok": ping_ok,
        "ready": port_open and ping_ok,
        "readiness_level": "transport",
        "transport_ready": port_open and ping_ok,
        "protocol_ready": None,
        "tool_ready": None,
        "detail": detail,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
    }


def _probe_status(*, ready: bool, required: bool) -> str:
    if ready:
        return "OK"
    return "FAIL" if required else "WARN"


def _completed_probe_result(
    result: dict[str, Any],
    required: set[str],
) -> dict[str, Any]:
    is_required = result["server"] in required
    result["required"] = is_required
    result["status"] = _probe_status(
        ready=bool(result["ready"]),
        required=is_required,
    )
    return result


def _timed_out_probe_result(
    name: str,
    catalog: dict[str, Any],
    required: set[str],
    overall_timeout: float,
) -> dict[str, Any]:
    is_required = name in required
    entry = catalog[name]
    return {
        "server": name,
        "url": f"http://127.0.0.1:{entry['port']}{entry.get('path') or '/mcp'}",
        "port_open": False,
        "ping_ok": False,
        "ready": False,
        "readiness_level": "transport",
        "transport_ready": False,
        "protocol_ready": None,
        "tool_ready": None,
        "detail": f"overall timeout after {overall_timeout:.1f}s",
        "elapsed_ms": round(overall_timeout * 1000),
        "required": is_required,
        "status": _probe_status(ready=False, required=is_required),
    }


def _run_profile_probes(
    catalog: dict[str, Any],
    selected_local: list[str],
    required: set[str],
    *,
    timeout: float,
    overall_timeout: float,
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + overall_timeout
    completed: queue.Queue[dict[str, Any]] = queue.Queue()

    def probe_one(name: str) -> None:
        try:
            result = _probe(
                name,
                catalog[name],
                min(timeout, max(0.001, deadline - time.monotonic())),
            )
        except Exception:
            result = _timed_out_probe_result(name, catalog, required, overall_timeout)
            result["detail"] = "probe failed"
        completed.put(result)

    # Diagnostics only: daemon workers cannot hold CLI shutdown past the budget.
    # Socket/HTTP operations also receive the remaining deadline. No worker
    # starts a service or writes reports; report publication stays on this thread.
    for name in selected_local:
        threading.Thread(target=probe_one, args=(name,), daemon=True).start()
    pending = set(selected_local)
    results = []
    while pending:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            result = completed.get(timeout=remaining)
        except queue.Empty:
            break
        pending.discard(result["server"])
        results.append(_completed_probe_result(result, required))
    results.extend(
        _timed_out_probe_result(name, catalog, required, overall_timeout)
        for name in pending
    )
    return sorted(results, key=lambda item: item["server"])


def _mcp_payload(
    profile: str,
    plan: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = sum(item["status"] == "FAIL" for item in results)
    warned = sum(item["status"] == "WARN" for item in results)
    migration_hint = None
    if profile not in DAILY_PROFILES:
        migration_hint = (
            "For daily readiness, select the stable/shared profile; "
            "this diagnostic does not rewrite persisted state."
        )
    return {
        "readiness_level": "transport",
        "protocol_ready": None,
        "tool_ready": None,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "profile": profile,
        "failed": failed,
        "warned": warned,
        "remote_or_external_skipped": _as_str_list(plan.get("remote_or_external")),
        "disabled_by_mode": _as_str_list(plan.get("disabled_by_mode")),
        "migration_hint": migration_hint,
        "results": results,
    }


def _write_mcp_payload(
    repo_root: Path, output_path: Path, payload: dict[str, Any]
) -> None:
    output = _governed_report_path(repo_root, output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.write_text(  # NOSONAR - confined by _governed_report_path
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def _print_mcp_payload(
    profile: str,
    required: set[str],
    selected_local: list[str],
    payload: dict[str, Any],
) -> None:
    print(
        f"MCP profile={profile} required={len(required)} "
        f"selected_local={len(selected_local)}"
    )
    if payload["migration_hint"]:
        print(f"[HINT] {payload['migration_hint']}")
    for item in payload["results"]:
        scope = "required" if item["required"] else "optional"
        print(
            f"[{item['status']}] {item['server']} {scope} "
            f"{item['url']} — {item['detail']}"
        )
    for name in payload["remote_or_external_skipped"]:
        print(f"[SKIP] {name} remote/auth-managed; inspect with 'codex mcp list'")
    print(
        f"Summary: failed={payload['failed']} warned={payload['warned']} "
        f"skipped={len(payload['remote_or_external_skipped'])}"
    )


def run_transport(
    repo_root: Path,
    profile: str,
    *,
    timeout: float,
    overall_timeout: float,
    output_json: bool,
    output_path: Path | None = None,
) -> int:
    plan = effective_profile_plan(profile_plan(profile, repo_root), repo_root)
    catalog_path = repo_root / "scripts/ops/runtime/mcp/shared-servers.json"
    catalog = cast(
        dict[str, Any], json.loads(catalog_path.read_text(encoding="utf-8"))["servers"]
    )
    required = set(_as_str_list(plan.get("required_local")))
    selected_local = sorted(required | set(_as_str_list(plan.get("optional_local"))))
    results = _run_profile_probes(
        catalog,
        selected_local,
        required,
        timeout=timeout,
        overall_timeout=overall_timeout,
    )
    payload = _mcp_payload(profile, plan, results)
    if output_path is not None:
        _write_mcp_payload(repo_root, output_path, payload)

    if output_json:
        print(json.dumps(payload, indent=2))
    else:
        _print_mcp_payload(profile, required, selected_local, payload)
    return 1 if payload["failed"] else 0


def run_routes(
    repo_root: Path,
    profile: str,
    *,
    codex_executable: Path | None,
    output_json: bool,
    output_path: Path | None = None,
) -> int:
    """Capture configuration through the native resolver without probing MCP."""
    from scripts.ai.codex.mcp_routes import route_snapshot
    from scripts.ai.codex.native_mcp_config import NativeConfigClient, NativeConfigError

    executable = str(codex_executable) if codex_executable else shutil.which("codex")
    if not executable:
        print(
            json.dumps(
                {
                    "status": "NOT_TESTED",
                    "detail": "native Codex executable unavailable",
                }
            )
        )
        return 1
    try:
        with NativeConfigClient(
            [executable, "app-server", "--stdio"], repo_root
        ) as client:
            capture = client.read()
        payload = route_snapshot(
            capture,
            expected=_as_str_list(profile_plan(profile, repo_root)["selected"]),
            project_profile=profile,
        )
    except (NativeConfigError, ValueError) as exc:
        print(json.dumps({"status": "NOT_TESTED", "detail": str(exc)}))
        return 1
    if output_path is not None:
        _write_mcp_payload(repo_root, output_path, payload)
    if output_json:
        print(json.dumps(payload, indent=2))
    else:
        print("Native effective MCP configuration (tool readiness NOT_TESTED)")
        print("Expected: " + ", ".join(_as_str_list(payload["expected"])))
        print("Effective: " + ", ".join(_as_str_list(payload["effective"])))
        print("Missing: " + ", ".join(_as_str_list(payload["missing"])))
    return 0


def _read_probe_plan(repo_root: Path, requested: Path) -> dict:
    """Read a bounded JSON plan inside the dedicated repository control area."""
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("probe plan must be repository-relative without traversal")
    physical_root = repo_root.resolve(strict=True)
    control_root = (physical_root / "reports/quality/mcp-controls").resolve(strict=True)
    if not control_root.is_relative_to(physical_root):
        raise ValueError("probe control area must remain inside the workspace")
    candidate = (physical_root / requested).resolve(strict=True)
    if not candidate.is_relative_to(control_root) or candidate.suffix != ".json":
        raise ValueError("probe plan must resolve under reports/quality/mcp-controls")
    with candidate.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("probe plan exceeds size limit")
    controls = json.loads(raw)
    if not isinstance(controls, dict):
        raise ValueError("probe plan must be a server/control object")
    return controls


def run_mcp(
    repo_root: Path,
    profile: str,
    *,
    output_json: bool,
    codex_executable: Path | None = None,
    output_path: Path | None = None,
    probe_plan: Path | None = None,
    start_approved_adapters: bool = False,
) -> int:
    """Inspect native routes; only an explicit control plan enables MCP calls."""
    from scripts.ai.codex.native_mcp_config import NativeConfigClient, NativeConfigError
    from scripts.ai.codex.mcp_readiness import readiness_report, SERVICE_EFFECTS
    from scripts.ai.mcp._check_env_keys import load_dotenv

    executable = str(codex_executable) if codex_executable else shutil.which("codex")
    if not executable:
        print(
            json.dumps(
                {
                    "status": "NOT_TESTED",
                    "detail": "native Codex executable unavailable",
                }
            )
        )
        return 1
    if output_path is not None:
        _governed_report_path(repo_root, output_path)
    controls = {}
    if probe_plan is not None:
        if not start_approved_adapters:
            raise ValueError("--probe-plan requires --start-approved-adapters")
        try:
            controls = _read_probe_plan(repo_root, probe_plan)
        except (OSError, ValueError):
            print(
                json.dumps(
                    {
                        "status": "NOT_TESTED",
                        "detail": "probe plan unavailable or invalid",
                    }
                )
            )
            return 1
        print(
            "MCP diagnostic service effects: " + "; ".join(SERVICE_EFFECTS),
            file=sys.stderr,
        )

    def capture():
        with NativeConfigClient(
            [executable, "app-server", "--stdio"], repo_root
        ) as client:
            return client.read()

    try:
        plan = profile_plan(profile, repo_root)
        payload = readiness_report(
            capture(),
            expected=_as_str_list(plan["selected"]),
            required=_as_str_list(plan["required"]),
            profile=profile,
            controls=controls,
            environment=load_dotenv(repo_root / ".env"),
            after=capture,
        )
    except (NativeConfigError, ValueError):
        print(
            json.dumps(
                {
                    "status": "NOT_TESTED",
                    "detail": "native configuration unavailable or invalid; raw data omitted",
                }
            )
        )
        return 1
    if output_path is not None:
        _write_mcp_payload(repo_root, output_path, payload)
    _print_readiness(payload, output_json)
    return 0 if payload["ready"] else 1


def _print_readiness(payload: dict, output_json: bool) -> None:
    if output_json:
        print(json.dumps(payload, indent=2))
        return
    for row in payload["results"]:
        print(f"[{row['status']}] {row['server']}: {row['detail']}")


def _governed_report_path(repo_root: Path, requested: Path) -> Path:
    """Resolve an explicit MCP report path under governed quality reports."""

    if requested.is_absolute():
        raise ValueError("--output must be repository-relative")
    if ".." in requested.parts:
        raise ValueError("--output must not contain parent traversal")
    candidate = repo_root / requested
    resolved = candidate.resolve()
    quality_root = (repo_root / "reports/quality").resolve()
    if not resolved.is_relative_to(quality_root):
        raise ValueError("--output must resolve under reports/quality")
    if resolved.suffix != ".json":
        raise ValueError("--output must use a .json suffix")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("static", "mcp", "all", "routes", "transport"),
        nargs="?",
        default="static",
    )
    parser.add_argument("--profile", choices=sorted(setup_mcp.MCP_PROFILES))
    parser.add_argument(
        "--codex-executable",
        type=Path,
        help="installed native Codex executable for routes mode",
    )
    parser.add_argument(
        "--probe-plan",
        type=Path,
        help="repository-relative JSON under reports/quality/mcp-controls",
    )
    parser.add_argument(
        "--start-approved-adapters",
        action="store_true",
        help="acknowledge declared service effects for the explicit control plan",
    )
    parser.add_argument("--timeout", type=float, help="legacy transport mode only")
    parser.add_argument(
        "--overall-timeout", type=float, help="legacy transport mode only"
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="suppress report output; adapter service effects require explicit opt-in",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="explicit JSON report path under reports/quality",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    profile = args.profile or setup_mcp.DEFAULT_LOCAL_PROFILE
    _validate_options(parser, args)
    return _dispatch(args, repo_root, profile)


def _validate_options(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    if args.no_write and args.output is not None:
        parser.error("--no-write and --output are mutually exclusive")
    if args.output is not None and args.mode == "static":
        parser.error("--output is only valid for mcp, all, or routes mode")

    if args.mode != "transport" and (
        args.timeout is not None or args.overall_timeout is not None
    ):
        parser.error(
            "--timeout/--overall-timeout belong to transport mode; MCP controls use native route limits"
        )
    if args.probe_plan and not args.start_approved_adapters:
        parser.error("--probe-plan requires --start-approved-adapters")


def _dispatch(args: argparse.Namespace, repo_root: Path, profile: str) -> int:
    if args.mode == "transport":
        return run_transport(
            repo_root,
            profile,
            timeout=max(0.1, args.timeout if args.timeout is not None else 1.0),
            overall_timeout=max(
                0.1, args.overall_timeout if args.overall_timeout is not None else 10.0
            ),
            output_json=args.json,
            output_path=args.output,
        )

    if args.mode == "routes":
        return run_routes(
            repo_root,
            profile,
            codex_executable=args.codex_executable,
            output_json=args.json,
            output_path=args.output,
        )

    static_status = 0
    if args.mode in {"static", "all"}:
        static_status = run_static(repo_root, output_json=args.json)
    live_status = 0
    if args.mode in {"mcp", "all"}:
        live_status = run_mcp(
            repo_root,
            profile,
            output_json=args.json,
            output_path=args.output,
            codex_executable=args.codex_executable,
            probe_plan=args.probe_plan,
            start_approved_adapters=args.start_approved_adapters,
        )
    return 1 if static_status or live_status else 0


if __name__ == "__main__":
    raise SystemExit(main())
