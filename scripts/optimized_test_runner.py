#!/usr/bin/env python3
"""
Optimized Test Runner for BioETL Project

This script provides focused test execution strategies to avoid timeouts
and improve developer productivity.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Test categories and their typical execution times
TEST_CATEGORIES = {
    "unit-fast": {
        "description": "Fastest unit tests (no I/O, no async)",
        "paths": ["tests/unit/domain/", "tests/unit/helpers/"],
        "markers": ["unit", "not slow"],
        "timeout": 120,
    },
    "unit-core": {
        "description": "Core unit tests including application layer",
        "paths": ["tests/unit/"],
        "markers": ["unit"],
        "exclude_markers": ["slow", "integration"],
        "timeout": 300,
    },
    "architecture": {
        "description": "Architecture tests (layer boundaries)",
        "paths": ["tests/architecture/"],
        "markers": ["architecture"],
        "timeout": 180,
    },
    "integration-core": {
        "description": "Core integration tests (with VCR)",
        "paths": ["tests/integration/"],
        "markers": ["integration", "not slow"],
        "timeout": 300,
    },
    "smoke": {
        "description": "Quick smoke tests",
        "paths": ["tests/smoke/"],
        "markers": ["smoke"],
        "timeout": 60,
    },
    "contract": {
        "description": "Contract tests",
        "paths": ["tests/contract/"],
        "markers": ["contract"],
        "timeout": 180,
    },
}


def run_pytest(
    paths: list[str],
    markers: list[str] | None = None,
    exclude_markers: list[str] | None = None,
    timeout: int = 300,
    verbose: bool = True,
    coverage: bool = False,
) -> bool:
    """Run pytest with specified configuration."""

    cmd = ["python3", "-m", "pytest"]

    # Add paths
    cmd.extend(paths)

    # Add markers
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])

    # Add exclude markers
    if exclude_markers:
        for marker in exclude_markers:
            cmd.extend(["-m", f"not {marker}"])

    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=src/bioetl/", "--cov-report=term-missing"])

    # Add timeout
    cmd.append(f"--timeout={timeout}")

    # Add other useful options
    cmd.extend(["--tb=short", "-x"])  # short traceback, stop on first failure

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 60,  # Add buffer
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"❌ Test execution timed out after {timeout} seconds", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}", file=sys.stderr)
        return False


def run_category(category: str, coverage: bool = False) -> bool:
    """Run tests for a specific category."""

    if category not in TEST_CATEGORIES:
        print(f"❌ Unknown category: {category}", file=sys.stderr)
        print(f"Available categories: {', '.join(TEST_CATEGORIES.keys())}")
        return False

    config = TEST_CATEGORIES[category]
    print(f"🚀 Running {category}: {config['description']}")
    print(f"Timeout: {config['timeout']} seconds")

    success = run_pytest(
        paths=config["paths"],
        markers=config.get("markers"),
        exclude_markers=config.get("exclude_markers"),
        timeout=config["timeout"],
        coverage=coverage,
    )

    if success:
        print(f"✅ {category} tests passed!")
    else:
        print(f"❌ {category} tests failed!")

    return success


def run_focused_test_module(module_path: str, coverage: bool = False) -> bool:
    """Run tests for a specific module."""

    if not module_path.startswith("tests/"):
        module_path = f"tests/{module_path}"

    if not Path(module_path).exists():
        print(f"❌ Module not found: {module_path}", file=sys.stderr)
        return False

    print(f"🚀 Running focused tests for: {module_path}")

    success = run_pytest(paths=[module_path], timeout=180, coverage=coverage)

    return success


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Optimized Test Runner for BioETL Project"
    )

    parser.add_argument(
        "target",
        nargs="?",
        default="unit-fast",
        help=f"Test category or module path. Categories: {', '.join(TEST_CATEGORIES.keys())}",
    )

    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage analysis"
    )

    parser.add_argument(
        "--list", action="store_true", help="List available test categories"
    )

    args = parser.parse_args()

    if args.list:
        print("Available Test Categories:")
        for name, config in TEST_CATEGORIES.items():
            print(
                f"  {name:15} - {config['description']} (timeout: {config['timeout']}s)"
            )
        return

    # Check if target is a category or module path
    if args.target in TEST_CATEGORIES:
        success = run_category(args.target, args.coverage)
    else:
        success = run_focused_test_module(args.target, args.coverage)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
