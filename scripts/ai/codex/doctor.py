#!/usr/bin/env python3
"""Static and bounded live diagnostics for the BioETL Codex runtime."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import socket
import time
import urllib.request
from pathlib import Path
from typing import Any, cast
import sys

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import setup_mcp  # pyright: ignore[reportImplicitRelativeImport]
from mcp_profile_contract import profile_plan, validate_profile_matrix  # pyright: ignore[reportImplicitRelativeImport]
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
                f"http://127.0.0.1:{port}/ping", timeout=timeout
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
        "detail": detail,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
    }


def _probe_status(result: dict[str, Any]) -> str:
    if result["ready"]:
        return "OK"
    return "FAIL" if result["required"] else "WARN"


def _completed_probe_results(
    done: set[concurrent.futures.Future[dict[str, Any]]], required: set[str]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for future in done:
        result = future.result()
        result["required"] = result["server"] in required
        result["status"] = _probe_status(result)
        results.append(result)
    return results


def _timed_out_probe_results(
    pending: set[concurrent.futures.Future[dict[str, Any]]],
    futures: dict[concurrent.futures.Future[dict[str, Any]], str],
    catalog: dict[str, Any],
    required: set[str],
    overall_timeout: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for future in pending:
        name = futures[future]
        future.cancel()
        required_server = name in required
        results.append(
            {
                "server": name,
                "url": f"http://127.0.0.1:{catalog[name]['port']}"
                f"{catalog[name].get('path') or '/mcp'}",
                "port_open": False,
                "ping_ok": False,
                "ready": False,
                "detail": f"overall timeout after {overall_timeout:.1f}s",
                "elapsed_ms": round(overall_timeout * 1000),
                "required": required_server,
                "status": "FAIL" if required_server else "WARN",
            }
        )
    return results


def _run_mcp_probes(
    *,
    selected_local: list[str],
    required: set[str],
    catalog: dict[str, Any],
    timeout: float,
    overall_timeout: float,
) -> list[dict[str, Any]]:
    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=min(8, len(selected_local) or 1)
    )
    futures = {
        pool.submit(_probe, name, catalog[name], timeout): name
        for name in selected_local
    }
    done, pending = concurrent.futures.wait(futures, timeout=overall_timeout)
    results = _completed_probe_results(done, required)
    results.extend(
        _timed_out_probe_results(pending, futures, catalog, required, overall_timeout)
    )
    pool.shutdown(wait=False, cancel_futures=True)
    return sorted(results, key=lambda item: item["server"])


def _mcp_probe_payload(
    *,
    profile: str,
    plan: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = sum(item["status"] == "FAIL" for item in results)
    warned = sum(item["status"] == "WARN" for item in results)
    return {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "profile": profile,
        "failed": failed,
        "warned": warned,
        "remote_or_external_skipped": _as_str_list(plan.get("remote_or_external")),
        "migration_hint": (
            None
            if profile in DAILY_PROFILES
            else "For daily readiness, select the stable/shared profile; "
            "this diagnostic does not rewrite persisted state."
        ),
        "results": results,
    }


def _write_mcp_probe_payload(
    repo_root: Path, output_path: Path | None, payload: dict[str, Any]
) -> None:
    if output_path is None:
        return
    output = _governed_report_path(repo_root, output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


def _print_mcp_probe_payload(
    *,
    profile: str,
    required: set[str],
    selected_local: list[str],
    plan: dict[str, Any],
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
    skipped = _as_str_list(plan.get("remote_or_external"))
    for name in skipped:
        print(f"[SKIP] {name} remote/auth-managed; inspect with 'codex mcp list'")
    print(
        f"Summary: failed={payload['failed']} warned={payload['warned']} "
        f"skipped={len(skipped)}"
    )


def run_mcp(
    repo_root: Path,
    profile: str,
    *,
    timeout: float,
    overall_timeout: float,
    output_json: bool,
    output_path: Path | None = None,
) -> int:
    plan = profile_plan(profile, repo_root)
    catalog_path = repo_root / "scripts/ops/runtime/mcp/shared-servers.json"
    catalog = cast(
        dict[str, Any], json.loads(catalog_path.read_text(encoding="utf-8"))["servers"]
    )
    required = set(_as_str_list(plan.get("required_local")))
    selected_local = sorted(required | set(_as_str_list(plan.get("optional_local"))))
    results = _run_mcp_probes(
        selected_local=selected_local,
        required=required,
        catalog=catalog,
        timeout=timeout,
        overall_timeout=overall_timeout,
    )
    payload = _mcp_probe_payload(profile=profile, plan=plan, results=results)
    _write_mcp_probe_payload(repo_root, output_path, payload)

    if output_json:
        print(json.dumps(payload, indent=2))
    else:
        _print_mcp_probe_payload(
            profile=profile,
            required=required,
            selected_local=selected_local,
            plan=plan,
            payload=payload,
        )
    return 1 if payload["failed"] else 0


def _governed_report_path(repo_root: Path, requested: Path) -> Path:
    """Resolve an explicit MCP report path under governed quality reports."""

    candidate = requested if requested.is_absolute() else repo_root / requested
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
        "mode", choices=("static", "mcp", "all"), nargs="?", default="static"
    )
    parser.add_argument("--profile", choices=sorted(setup_mcp.MCP_PROFILES))
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--overall-timeout", type=float, default=10.0)
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="compatibility flag; diagnostics are read-only unless --output is set",
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
    if args.no_write and args.output is not None:
        parser.error("--no-write and --output are mutually exclusive")
    if args.output is not None and args.mode == "static":
        parser.error("--output is only valid for mcp or all mode")

    static_status = 0
    if args.mode in {"static", "all"}:
        static_status = run_static(repo_root, output_json=args.json)
    live_status = 0
    if args.mode in {"mcp", "all"}:
        live_status = run_mcp(
            repo_root,
            profile,
            timeout=max(0.1, args.timeout),
            overall_timeout=max(0.1, args.overall_timeout),
            output_json=args.json,
            output_path=args.output,
        )
    return 1 if static_status or live_status else 0


if __name__ == "__main__":
    raise SystemExit(main())
