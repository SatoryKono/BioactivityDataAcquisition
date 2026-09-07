#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/ci/ commands.

Usage:
    python -m scripts.engineering.ci <command> [args...]
    python -m scripts.engineering.ci --help

Commands:
    run-tests       Run pytest with resilient retry logic
    quality-gate    Integral quality gate for CI
    architecture-junit-skips  Fail closed on empty/skipped architecture JUnit
    pr-gate         Classify and aggregate required PR checks
    e2e-skip-rate   Check E2E matrix skip rate against threshold
    e2e-rerun       Check E2E rerun stability
    gitleaks-boundaries  Verify Gitleaks false-positive exception boundaries
    neo4j-memory    Check deterministic Neo4j memory ontology invariants
    neo4j-memory-live  Apply deterministic sync and validate live Neo4j drift
    docker-timing   Report Docker workflow timing and capacity evidence
    pr-gate-timing  Report PR Gate Complete timing and capacity evidence
    debt-report     Generate weekly quality debt report
    apply-ci-fixes  Apply one-off hosted GitHub workflow fixes
"""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.engineering.common.cli_dispatch import (
    dispatch_cli,
    python_command,
)

COMMANDS = {
    "run-tests": "run_pytest_resilient.py",
    "quality-gate": "quality_integral_gate.py",
    "architecture-junit-skips": "quality_integral_gate.py",
    "pr-gate": "pr_gate.py",
    "e2e-skip-rate": "check_e2e_matrix_skip_rate.py",
    "e2e-rerun": "check_e2e_rerun_stability.py",
    "neo4j-memory": "check_neo4j_memory_ontology.py",
    "neo4j-memory-live": "check_neo4j_memory_live_audit.py",
    "docker-timing": "report_docker_actions_timing.py",
    "pr-gate-timing": "report_pr_gate_timing.py",
    "debt-report": "report_quality_debt_weekly.py",
    "apply-ci-fixes": "apply_ci_fixes.py",
}
COMMAND_SPECS = {name: python_command(script) for name, script in COMMANDS.items()}

_DIR = Path(__file__).parent


def _gitleaks_boundaries(argv: list[str]) -> int:
    """Run the scanner regression suite through the existing CI entry point."""
    import argparse
    import hashlib
    import json
    import shutil
    import subprocess
    import tempfile

    repo_root = Path(__file__).resolve().parents[3]
    TOKEN = hashlib.sha256(
        b"nonfunctional regression sentinel for issue 10136"
    ).hexdigest()
    CASES: list[tuple[str, str, str, bool]] = []

    def pair(
        name: str, path: str, allowed: str, extra_positive: str | None = None
    ) -> None:
        CASES.append((name + "-allowed", path, allowed, False))
        CASES.append(
            (
                name + "-credential-same-path",
                path,
                extra_positive or 'api_key = "' + TOKEN + '"\n',
                True,
            )
        )
        CASES.append((name + "-outside-path", "unrelated/evidence.txt", allowed, True))

    def curl_user(value: str) -> str:
        """Construct test commands without a credential literal in this source file."""
        return " ".join(("curl", "-u", value, "http://localhost")) + "\n"

    pair(
        "sonar",
        "reports/quality/sonar/live-issues-20260820-rf009-full.json",
        '"key": "' + TOKEN[:20] + '"\n',
    )
    pair(
        "biology",
        "data/output/chembl_target.csv",
        f"CHEMBL1,homo {'sapiens'},{'5-hydroxytryptamine'} receptor 1d,9606\n",
    )
    pair(
        "hash",
        "tests/unit/domain/hash_policy/snapshots/chembl_high_risk_hashes.json",
        '"target_component_key_order_a": "' + TOKEN + '",\n',
    )
    pair(
        "row-key",
        "configs/field_registry/semantic_pair_matrix_budget.yaml",
        f"row_key: {'fc974cabe46e3021'}\n",
    )
    pair(
        "graph",
        "src/bioetl_knowledge_graph_expanded.json",
        json.dumps(
            ["accession", "=".join(["normalized", "true"]), "write_mode"],
            separators=(",", ":"),
        )
        + "\n",
    )
    pair(
        "narrative",
        "src/memory/episodic/summaries/full-tech-debt-audit-main-2026-06-19.md",
        "Key findings" + ": " + "compatibility/facade\n",
    )
    pair(
        "memory-dummy",
        "tests/unit/memory/test_security.py",
        'secret = "ghp_' + "abcdefghijklmnopqrstuvwxyz123456" + '"\n',
    )
    pair(
        "token-dummy",
        "tests/unit/repo_backed/scripts/ai/mcp/test_token_validation_helpers.py",
        'env={"TEST_TOKEN": "ghp_' + "12345678901234567890" + '"}\n',
    )
    pair(
        "collector-dummy",
        "tests/unit/infrastructure/adapters/common/test_api_request_collector.py",
        '"api_key": "secret_' + 'key_12345",\n',
    )
    pair(
        "docs-dummy",
        "docs/03-guides/github-setup-plan.md",
        'API_KEY = "sk-' + '1234567890"\n',
    )
    pair(
        "curl-placeholder",
        "docs/05-operations/verification/endpoint-validation-checklist.md",
        'curl -H "Authorization: Bearer YOUR_API_KEY" https://example.invalid\n',
        'curl -H "Authorization: Bearer ' + TOKEN + '" https://example.invalid\n',
    )
    pair(
        "powershell",
        "docs/05-operations/deployment/neo4j-audit-instance-implementation.md",
        curl_user('"${env:NEO4J_AUDIT_USERNAME}:${env:NEO4J_AUDIT_PASSWORD}"'),
        curl_user('"neo4j:' + TOKEN + '"'),
    )
    pair(
        "ellipsis",
        "docs/MCP_MEMORY_OPERATIONAL.md",
        curl_user("neo4j:..."),
        curl_user("neo4j:" + TOKEN),
    )

    # Match-based exceptions must not discard a second assignment on the same line.
    CASES.append(
        (
            "sonar-adjacent-credential",
            "reports/quality/sonar/live-issues-20260820-rf009-full.json",
            '"key": "' + TOKEN[:20] + '", "api_key": "' + TOKEN + '"\n',
            True,
        )
    )
    CASES.append(
        (
            "csv-adjacent-credential",
            "data/output/chembl_target.csv",
            f'homo {"sapiens"},{"5-hydroxytryptamine"} receptor,api_key="'
            + TOKEN
            + '"\n',
            True,
        )
    )

    def main() -> int:
        parser = argparse.ArgumentParser(
            description="Check Gitleaks exception boundaries with the pinned scanner"
        )
        parser.add_argument("--binary", default=shutil.which("gitleaks"))
        parser.add_argument("--config", type=Path, default=repo_root / ".gitleaks.toml")
        parser.add_argument("--report", type=Path)
        args = parser.parse_args(argv)
        if not args.binary:
            parser.error("gitleaks 8.24.3 is required; provide --binary")
        binary = str(Path(args.binary).resolve())
        config = args.config.resolve()
        version = subprocess.run(
            [binary, "version"], check=True, capture_output=True, text=True
        ).stdout.strip()
        if version != "8.24.3":
            parser.error(f"expected Gitleaks 8.24.3, received {version}")
        results = []
        with tempfile.TemporaryDirectory(prefix="bioetl-gitleaks-probes-") as temporary:
            base = Path(temporary).resolve()
            for i, (name, path, content, expected) in enumerate(CASES):
                root = base / str(i)
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                report = base / f"{i}.json"
                run = subprocess.run(
                    [
                        binary,
                        "dir",
                        ".",
                        "--config",
                        str(config),
                        "--redact",
                        "--no-banner",
                        "--report-format",
                        "json",
                        "--report-path",
                        str(report),
                    ],
                    capture_output=True,
                    cwd=root,
                    check=False,
                )
                findings = (
                    json.loads(report.read_text(encoding="utf-8"))
                    if report.exists()
                    else []
                )
                detected = bool(findings)
                passed = detected == expected and run.returncode == int(expected)
                results.append(
                    {
                        "name": name,
                        "expected_detection": expected,
                        "detected": detected,
                        "exit_code": run.returncode,
                        "passed": passed,
                        "rules": sorted({f["RuleID"] for f in findings}),
                    }
                )
                print(f"{name}: {'PASS' if passed else 'FAIL'}", flush=True)
        result = {
            "version": version,
            "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
            "passed": sum(r["passed"] for r in results),
            "total": len(results),
            "cases": results,
        }
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
        print(f"Passed {result['passed']}/{result['total']}")
        return int(not all(r["passed"] for r in results))

    return main()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "gitleaks-boundaries":
        return _gitleaks_boundaries(argv[1:])
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
        base_dir=_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
