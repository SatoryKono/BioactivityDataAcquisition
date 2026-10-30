"""Run the accepted real-backend schema matrix, failing closed on missing evidence.

The canonical schema-parity step owns this command. The optional negative control
changes only a synthetic fixture's expected type, never product data or contracts.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NEGATIVE_CONTROL_ENV = "BIOETL_PHYSICAL_PARITY_NEGATIVE_CONTROL"
TARGETS = (
    "tests/integration/infrastructure/storage/test_issue_12475_physical_parity.py",
    "tests/integration/infrastructure/storage/test_gold_writer_versioning.py",
    "tests/unit/domain/exceptions/test_storage.py",
    "tests/unit/infrastructure/storage/test_silver_writer_validation.py",
    "tests/unit/infrastructure/storage/silver_writer/test_silver_writer_schema.py",
    "tests/e2e/test_pipeline_with_schema_drift_e2e.py",
    "tests/integration/infrastructure/storage/test_issue_12474_parity_control.py",
)


def validate_junit(path: Path, targets: tuple[str, ...] = TARGETS) -> list[str]:
    """Require passing, nonempty, unskipped evidence for every selected module."""
    if not targets:
        return ["empty parity selection"]
    if not path.is_file():
        return ["missing parity JUnit"]
    try:
        cases = list(ET.parse(path).getroot().iter("testcase"))
    except (ET.ParseError, OSError) as exc:
        return [f"unreadable parity JUnit: {exc}"]
    errors = []
    if not cases:
        errors.append("empty parity JUnit")
    for case in cases:
        for tag in ("failure", "error", "skipped"):
            if case.find(tag) is not None:
                errors.append(f"{case.get('classname')}.{case.get('name')}: {tag}")
    for target in targets:
        module = target.removesuffix(".py").replace("/", ".")
        if not any(
            (case.get("classname") or "") == module
            or (case.get("classname") or "").startswith(module + ".")
            for case in cases
        ):
            errors.append(f"missing parity module: {target}")
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run one canonical matrix with real Delta/Arrow and preserve its JUnit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--negative-control", action="store_true")
    args = parser.parse_args(argv)
    missing = [target for target in TARGETS if not (REPO_ROOT / target).is_file()]
    if not TARGETS or missing:
        print(f"Missing/empty mandatory parity selection: {missing}", file=sys.stderr)
        return 2
    for backend in ("deltalake", "pyarrow", "zstandard"):
        if importlib.util.find_spec(backend) is None:
            print(f"Missing mandatory parity backend: {backend}", file=sys.stderr)
            return 2
    junit = args.junit.resolve()
    junit.parent.mkdir(parents=True, exist_ok=True)
    if junit.exists():
        print(f"Refusing stale parity evidence: {junit}", file=sys.stderr)
        return 2
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    # Ambient values cannot accidentally enable or mask the controlled run.
    env[NEGATIVE_CONTROL_ENV] = "1" if args.negative_control else "0"
    command = [
        sys.executable,
        "-m",
        "pytest",
        *TARGETS,
        "-q",
        "-o",
        "addopts=",
        "--strict-markers",
        "--strict-config",
        "-o",
        "xfail_strict=true",
        "--import-mode=importlib",
        "-p",
        "no:benchmark",
        "--junitxml",
        str(junit),
    ]
    print(f"physical parity argv={command!r}; cwd={REPO_ROOT}", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
    errors = validate_junit(junit)
    for error in errors:
        print(error, file=sys.stderr)
    return result.returncode or int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
