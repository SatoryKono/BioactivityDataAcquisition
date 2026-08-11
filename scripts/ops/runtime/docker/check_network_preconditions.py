#!/usr/bin/env python3
"""Check Docker network preconditions for BioETL helper stacks (MEDIUM gate).

External networks are contracted in docker_runtime_contracts.yaml:

- bioetl-monitoring — main + monitoring (scrape bioetl:8000, Ops HTTP)
- bioetl-runtime — main + neo4j

Raw ``docker compose -f docker-compose.monitoring.yml up`` fails with
"network bioetl-monitoring declared as external, but could not be found"
unless the network already exists. Prefer::

    python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring

By default this checker is read-only. Pass ``--ensure`` to create **missing**
contracted networks with the owner label (never deletes; refuses owner drift).

Stack → networks (from contract):

- ``monitoring`` → ``bioetl-monitoring`` only (not bioetl-runtime)
- ``main`` → ``bioetl-monitoring`` + ``bioetl-runtime``
- ``neo4j`` → ``bioetl-runtime``
- ``all`` → both shared networks
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONTRACT = Path("configs/quality/docker_runtime_contracts.yaml")
OWNER_LABEL = "com.bioetl.owner"
EXPECTED_OWNER = "scripts/ops/runtime/docker/runtime_manager.py"


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    code: str
    message: str
    evidence: dict[str, Any]


def _run(args: list[str], *, timeout: float = 15.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return 127, "", "docker executable not found"
    except subprocess.TimeoutExpired:
        return 124, "", "docker command timed out"
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _load_contract(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"contract must be a mapping: {path}")
    return payload


def ensure_shared_network(name: str, *, expected_owner: str) -> CheckResult:
    """Create network if missing; never overwrite foreign ownership."""
    code, _out, _err = _run(
        [
            "docker",
            "network",
            "inspect",
            "--format",
            '{{ index .Labels "com.bioetl.owner" }}',
            name,
        ]
    )
    if code == 0:
        return CheckResult(
            ok=True,
            code="NETWORK_ALREADY_EXISTS",
            message=f"Network {name!r} already present (ensure skipped create)",
            evidence={"network": name},
        )
    c_code, c_out, c_err = _run(
        [
            "docker",
            "network",
            "create",
            "--label",
            f"{OWNER_LABEL}={expected_owner}",
            name,
        ]
    )
    if c_code != 0:
        return CheckResult(
            ok=False,
            code="NETWORK_CREATE_FAILED",
            message=f"Failed to create network {name!r}",
            evidence={
                "network": name,
                "stderr": c_err[:500],
                "stdout": c_out[:300],
            },
        )
    return CheckResult(
        ok=True,
        code="NETWORK_CREATED",
        message=f"Created external network {name!r} with owner label",
        evidence={"network": name, "owner": expected_owner},
    )


def check_shared_network(name: str, *, expected_owner: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    code, out, err = _run(
        [
            "docker",
            "network",
            "inspect",
            "--format",
            "{{json .}}",
            name,
        ]
    )
    if code != 0:
        results.append(
            CheckResult(
                ok=False,
                code="NETWORK_MISSING",
                message=(
                    f"External network {name!r} is missing. "
                    "Create via --ensure or runtime_manager start "
                    "(not bare docker network create without owner label)."
                ),
                evidence={
                    "network": name,
                    "stderr": err[:500],
                    "remediation": (
                        "python scripts/ops/runtime/docker/check_network_preconditions.py "
                        f"--stack all --ensure"
                    ),
                },
            )
        )
        return results

    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        results.append(
            CheckResult(
                ok=False,
                code="NETWORK_INSPECT_PARSE",
                message=f"Could not parse docker network inspect for {name!r}",
                evidence={"network": name, "stdout": out[:300]},
            )
        )
        return results

    labels = payload.get("Labels") or {}
    owner = labels.get(OWNER_LABEL) or labels.get("com.bioetl.owner")
    if owner != expected_owner:
        results.append(
            CheckResult(
                ok=False,
                code="NETWORK_OWNER_DRIFT",
                message=(
                    f"Network {name!r} owner label mismatch "
                    f"(expected {expected_owner!r}, got {owner!r}). "
                    "Manager will not auto-delete; resolve ownership manually."
                ),
                evidence={
                    "network": name,
                    "expected_owner": expected_owner,
                    "observed_owner": owner,
                },
            )
        )
    else:
        results.append(
            CheckResult(
                ok=True,
                code="NETWORK_OK",
                message=f"Network {name!r} exists with contracted owner",
                evidence={"network": name, "owner": owner},
            )
        )
    return results


def check_bioetl_on_monitoring() -> list[CheckResult]:
    """Prometheus scrape + Grafana Ops HTTP require bioetl on bioetl-monitoring."""
    code, out, err = _run(
        [
            "docker",
            "inspect",
            "--format",
            "{{json .NetworkSettings.Networks}}",
            "bioetl",
        ]
    )
    if code != 0:
        return [
            CheckResult(
                ok=True,  # warn-level for monitoring-only hosts
                code="BIOETL_NOT_RUNNING",
                message=(
                    "Container 'bioetl' not running. Monitoring can start, but "
                    "scrape of bioetl:8000 and Ops HTTP identity will fail until "
                    "main stack is up on bioetl-monitoring."
                ),
                evidence={"stderr": err[:300], "severity": "warning"},
            )
        ]

    try:
        networks = json.loads(out)
    except json.JSONDecodeError:
        return [
            CheckResult(
                ok=False,
                code="BIOETL_NETWORK_PARSE",
                message="Could not parse bioetl network attachments",
                evidence={"stdout": out[:300]},
            )
        ]

    names = list(networks.keys()) if isinstance(networks, dict) else []
    if "bioetl-monitoring" not in names:
        return [
            CheckResult(
                ok=False,
                code="BIOETL_NOT_ON_MONITORING_NETWORK",
                message=(
                    "Container 'bioetl' is not attached to bioetl-monitoring. "
                    "Prometheus cannot scrape bioetl:8000; Grafana Ops HTTP "
                    "identity gate will defer/fail."
                ),
                evidence={
                    "attached": names,
                    "remediation": (
                        "python scripts/ops/runtime/docker/runtime_manager.py "
                        "start --stack main"
                    ),
                },
            )
        ]

    return [
        CheckResult(
            ok=True,
            code="BIOETL_ON_MONITORING_NETWORK",
            message="bioetl is attached to bioetl-monitoring (scrape/Ops HTTP path OK)",
            evidence={"attached": names},
        )
    ]


def _networks_for_stack(
    contract: dict[str, Any], stack: str
) -> list[tuple[str, str]]:
    """Return (name, owner) pairs contracted for stack."""
    shared = contract.get("shared_networks") or {}
    out: list[tuple[str, str]] = []
    for _logical, raw in shared.items():
        if not isinstance(raw, dict):
            continue
        consumers = raw.get("consumers") or []
        if stack not in consumers and stack != "all":
            continue
        name = str(raw.get("name") or "")
        owner = str(raw.get("owner") or EXPECTED_OWNER)
        if name:
            out.append((name, owner))
    return out


def run_checks(
    *, stack: str, contract_path: Path, ensure: bool = False
) -> list[CheckResult]:
    contract = _load_contract(contract_path)
    results: list[CheckResult] = []

    for name, owner in _networks_for_stack(contract, stack):
        if ensure:
            # Create if missing, then re-check ownership.
            ensure_result = ensure_shared_network(name, expected_owner=owner)
            results.append(ensure_result)
            if not ensure_result.ok:
                continue
        results.extend(check_shared_network(name, expected_owner=owner))

    if stack in {"monitoring", "all", "main"}:
        results.extend(check_bioetl_on_monitoring())

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check BioETL Docker network preconditions. "
            "monitoring → bioetl-monitoring only; main → monitoring+runtime."
        )
    )
    parser.add_argument(
        "--stack",
        default="monitoring",
        choices=["main", "monitoring", "neo4j", "all"],
        help="Stack whose contracted networks to validate",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT,
        help="Path to docker_runtime_contracts.yaml",
    )
    parser.add_argument(
        "--ensure",
        action="store_true",
        help="Create missing contracted networks with owner label (no delete)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    args = parser.parse_args(argv)

    contract_path = args.contract
    if not contract_path.is_file():
        contract_path = _REPO_ROOT / args.contract
    if not contract_path.is_file():
        print(f"ERROR: contract not found: {args.contract}", file=sys.stderr)
        return 2

    results = run_checks(
        stack=args.stack, contract_path=contract_path, ensure=args.ensure
    )
    hard_fail = [
        r for r in results if not r.ok and r.evidence.get("severity") != "warning"
    ]
    warnings = [
        r
        for r in results
        if (not r.ok and r.evidence.get("severity") == "warning")
        or r.code == "BIOETL_NOT_RUNNING"
    ]

    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": "bioetl-docker-network-preconditions-v1",
                    "stack": args.stack,
                    "ensure": args.ensure,
                    "ok": not hard_fail,
                    "results": [
                        {
                            "ok": r.ok,
                            "code": r.code,
                            "message": r.message,
                            "evidence": r.evidence,
                        }
                        for r in results
                    ],
                },
                indent=2,
            )
        )
    else:
        mode = "ensure+check" if args.ensure else "check"
        print(f"=== Network preconditions (stack={args.stack}, mode={mode}) ===")
        if args.stack == "monitoring":
            print("Note: monitoring compose requires bioetl-monitoring only "
                  "(not bioetl-runtime).")
        elif args.stack == "main":
            print("Note: main compose requires bioetl-monitoring + bioetl-runtime.")
        for r in results:
            mark = (
                "OK "
                if r.ok
                else (
                    "WARN"
                    if r.evidence.get("severity") == "warning"
                    or r.code == "BIOETL_NOT_RUNNING"
                    else "FAIL"
                )
            )
            print(f"[{mark}] {r.code}: {r.message}")
            rem = r.evidence.get("remediation")
            if rem:
                print(f"       remediation: {rem}")
        if hard_fail:
            print(
                "\nFAIL: fix network preconditions before compose up "
                "(--ensure or runtime_manager start)."
            )
        elif warnings:
            print("\nWARN: stack may start degraded (see messages above).")
        else:
            print("\nOK: network preconditions satisfied.")

    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
