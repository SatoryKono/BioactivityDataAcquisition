#!/usr/bin/env python3
"""Deterministic preflight for repo-backed Prometheus rules."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

RULES_FILE = Path("grafana/prometheus-rules/bioetl_observability.yml")
TESTS_FILE = Path("grafana/prometheus-rules/tests/bioetl_observability.test.yml")
PROMETHEUS_IMAGE = "prom/prometheus:v2.54.1"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run promtool syntax and rule-vector validation for BioETL "
            "Prometheus rules."
        )
    )
    parser.add_argument("--rules-file", type=Path, default=RULES_FILE)
    parser.add_argument("--test-file", type=Path, default=TESTS_FILE)
    parser.add_argument(
        "--runner",
        choices=("local", "docker"),
        default="local",
        help="Use local promtool or the pinned Prometheus Docker image.",
    )
    parser.add_argument(
        "--promtool",
        default="promtool",
        help="promtool executable name/path for --runner local.",
    )
    parser.add_argument(
        "--image",
        default=PROMETHEUS_IMAGE,
        help="Docker image for --runner docker.",
    )
    return parser


def _run(command: list[str]) -> int:
    print("+ " + " ".join(command))
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def _missing_promtool_message(promtool: str) -> str:
    return (
        f"promtool executable not found: {promtool!r}. "
        "Install Prometheus promtool, or run the deterministic Docker-backed "
        "surface: python -m scripts.engineering.qa check-prometheus-rules "
        "--runner docker."
    )


def _run_local(*, promtool: str, rules_file: Path, test_file: Path) -> int:
    resolved = shutil.which(promtool)
    if resolved is None:
        print(_missing_promtool_message(promtool), file=sys.stderr)
        return 127
    checks = [
        [resolved, "check", "rules", str(rules_file)],
        [resolved, "test", "rules", str(test_file)],
    ]
    for command in checks:
        result = _run(command)
        if result != 0:
            return result
    return 0


def _run_docker(*, image: str, rules_file: Path, test_file: Path) -> int:
    docker = shutil.which("docker")
    if docker is None:
        print(
            "docker executable not found for --runner docker. "
            "Install Docker or run with --runner local after installing promtool.",
            file=sys.stderr,
        )
        return 127
    workspace = Path.cwd()
    checks = [
        ["check", "rules", str(rules_file)],
        ["test", "rules", str(test_file)],
    ]
    for check in checks:
        command = [
            docker,
            "run",
            "--rm",
            "-v",
            f"{workspace}:/workspace",
            "-w",
            "/workspace",
            "--entrypoint",
            "promtool",
            image,
            *check,
        ]
        result = _run(command)
        if result != 0:
            return result
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.runner == "docker":
        return _run_docker(
            image=args.image,
            rules_file=args.rules_file,
            test_file=args.test_file,
        )
    return _run_local(
        promtool=args.promtool,
        rules_file=args.rules_file,
        test_file=args.test_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
