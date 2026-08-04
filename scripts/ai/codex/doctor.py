#!/usr/bin/env python3
"""Static and bounded live diagnostics for the BioETL Codex runtime."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import socket
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import setup_mcp
from mcp_profile_contract import profile_plan, validate_profile_matrix
from native_runtime_contract import Finding, REPO_ROOT, validate_native_runtime


WINDOWS_STREAMING_MODES = {"windows_docker_streaming", "windows_npx_streaming"}
DAILY_PROFILES = {"stable", "shared"}


def selected_profile(repo_root: Path) -> str:
    override = os.environ.get("CODEX_MCP_PROFILE", "").strip()
    if override:
        return override
    state = repo_root / ".codex/mcp-profile.json"
    if state.is_file():
        try:
            value = json.loads(state.read_text(encoding="utf-8")).get("profile")
            if value:
                return str(value)
        except (OSError, json.JSONDecodeError):
            pass
    return setup_mcp.DEFAULT_LOCAL_PROFILE


def run_static(repo_root: Path, *, output_json: bool = False) -> int:
    findings = validate_native_runtime(repo_root)
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
    port_open = False
    ping_ok = False
    detail = "connection refused or timed out"
    url = ""
    try:
        port = int(entry["port"])
        path = str(entry.get("path") or "/mcp")
        url = f"http://127.0.0.1:{port}{path}"
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


def run_mcp(
    repo_root: Path,
    profile: str,
    *,
    timeout: float,
    overall_timeout: float,
    no_write: bool,
    output_json: bool,
) -> int:
    plan = profile_plan(profile, repo_root)
    catalog_path = repo_root / "scripts/ops/runtime/mcp/shared-servers.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))["servers"]
    required = set(plan["required_local"])
    selected_local = sorted(required | set(plan["optional_local"]))
    results: list[dict[str, Any]] = []

    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=min(8, len(selected_local) or 1)
    )
    futures = {
        pool.submit(_probe, name, catalog[name], timeout): name
        for name in selected_local
    }
    done, pending = concurrent.futures.wait(futures, timeout=overall_timeout)
    for future in done:
        name = futures[future]
        try:
            result = future.result()
        except Exception as exc:
            result = {
                "server": name,
                "url": "",
                "port_open": False,
                "ping_ok": False,
                "ready": False,
                "detail": f"{type(exc).__name__}: {exc}",
                "elapsed_ms": 0,
            }
        result["required"] = result["server"] in required
        result["status"] = (
            "OK" if result["ready"] else "FAIL" if result["required"] else "WARN"
        )
        results.append(result)
    for future in pending:
        name = futures[future]
        future.cancel()
        results.append(
            {
                "server": name,
                "url": f"http://127.0.0.1:{catalog[name]['port']}{catalog[name].get('path') or '/mcp'}",
                "port_open": False,
                "ping_ok": False,
                "ready": False,
                "detail": f"overall timeout after {overall_timeout:.1f}s",
                "elapsed_ms": round(overall_timeout * 1000),
                "required": name in required,
                "status": "FAIL" if name in required else "WARN",
            }
        )
    pool.shutdown(wait=False, cancel_futures=True)
    results.sort(key=lambda item: item["server"])

    failed = sum(item["status"] == "FAIL" for item in results)
    warned = sum(item["status"] == "WARN" for item in results)
    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "profile": profile,
        "failed": failed,
        "warned": warned,
        "remote_or_external_skipped": plan["remote_or_external"],
        "migration_hint": (
            None
            if profile in DAILY_PROFILES
            else "For daily readiness, select the stable/shared profile; "
            "this diagnostic does not rewrite persisted state."
        ),
        "results": results,
    }
    if not no_write:
        output = repo_root / "logs/mcp-shared/health.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)

    if output_json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"MCP profile={profile} required={len(required)} selected_local={len(selected_local)}"
        )
        if payload["migration_hint"]:
            print(f"[HINT] {payload['migration_hint']}")
        for item in results:
            scope = "required" if item["required"] else "optional"
            print(
                f"[{item['status']}] {item['server']} {scope} {item['url']} — {item['detail']}"
            )
        for name in plan["remote_or_external"]:
            print(f"[SKIP] {name} remote/auth-managed; inspect with 'codex mcp list'")
        print(
            f"Summary: failed={failed} warned={warned} skipped={len(plan['remote_or_external'])}"
        )
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("static", "mcp", "all"), nargs="?", default="static"
    )
    parser.add_argument("--profile", choices=sorted(setup_mcp.MCP_PROFILES))
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--overall-timeout", type=float, default=10.0)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    profile = args.profile or selected_profile(repo_root)
    if profile not in setup_mcp.MCP_PROFILES:
        print(
            f"[FAIL] Unknown MCP profile '{profile}'; choose one of: "
            f"{', '.join(sorted(setup_mcp.MCP_PROFILES))}"
        )
        return 1

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
            no_write=args.no_write,
            output_json=args.json,
        )
    return 1 if static_status or live_status else 0


if __name__ == "__main__":
    raise SystemExit(main())
