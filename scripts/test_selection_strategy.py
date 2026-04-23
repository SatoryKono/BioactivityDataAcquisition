#!/usr/bin/env python3
"""
Test Selection Strategy Implementation

Implements the test selection strategy from py-test-bot documentation
to run appropriate tests based on changed files.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

# Test selection strategy based on file changes
TEST_SELECTION_STRATEGY = {
    "domain": {
        "trigger_files": ["src/bioetl/domain/"],
        "test_paths": [
            "tests/unit/domain/",
            "tests/architecture/"
        ],
        "description": "Domain layer changes - run unit and architecture tests"
    },
    "application": {
        "trigger_files": ["src/bioetl/application/"],
        "test_paths": [
            "tests/unit/application/",
            "tests/integration/application/"
        ],
        "description": "Application layer changes - run unit and related integration tests"
    },
    "infrastructure_adapters": {
        "trigger_files": ["src/bioetl/infrastructure/adapters/"],
        "test_paths": [
            "tests/unit/infrastructure/adapters/",
            "tests/integration/"
        ],
        "description": "Adapter changes - run unit and integration tests for the provider"
    },
    "composition": {
        "trigger_files": ["src/bioetl/composition/"],
        "test_paths": [
            "tests/unit/composition/",
            "tests/architecture/"
        ],
        "description": "Composition changes - run unit and architecture tests"
    },
    "interfaces": {
        "trigger_files": ["src/bioetl/interfaces/"],
        "test_paths": [
            "tests/unit/interfaces/"
        ],
        "description": "Interface changes - run interface unit tests"
    },
    "configs": {
        "trigger_files": ["configs/"],
        "test_paths": [
            "tests/integration/"
        ],
        "description": "Configuration changes - run integration tests"
    },
    "python_files": {
        "trigger_files": ["*.py"],
        "test_paths": [
            "tests/architecture/"
        ],
        "pre_check": ["make lint"],
        "description": "Any Python file change - run linting and architecture tests"
    }
}


def detect_changed_files(git_diff_target: str = "HEAD") -> Set[str]:
    """Detect changed files using git diff."""
    
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", git_diff_target],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"⚠️  Git diff failed: {result.stderr}")
            return set()
            
        changed_files = set(result.stdout.strip().split('\n'))
        changed_files.discard('')  # Remove empty entries
        
        return changed_files
        
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"❌ Error detecting changed files: {e}")
        return set()


def match_files_to_strategy(changed_files: Set[str]) -> List[str]:
    """Match changed files to test selection strategies."""

    matched_strategies = [
        strategy_name
        for strategy_name, strategy in TEST_SELECTION_STRATEGY.items()
        if _strategy_matches_changed_files(strategy, changed_files)
    ]
    _append_python_strategy_if_needed(matched_strategies, changed_files)
    return matched_strategies


def run_tests_for_strategy(strategy_name: str, coverage: bool = False) -> bool:
    """Run tests for a specific strategy."""

    if strategy_name not in TEST_SELECTION_STRATEGY:
        print(f"❌ Unknown strategy: {strategy_name}")
        return False

    strategy = TEST_SELECTION_STRATEGY[strategy_name]
    print(f"🚀 Running tests for strategy: {strategy_name}")
    print(f"Description: {strategy['description']}")

    if not _run_pre_checks(strategy):
        return False

    cmd = _build_pytest_command(strategy, coverage=coverage)
    print(f"Running: {' '.join(cmd)}")

    try:
        return _execute_strategy_command(strategy_name, cmd)
    except subprocess.TimeoutExpired:
        print("❌ Test execution timed out after 15 minutes", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}", file=sys.stderr)
        return False


def _execute_strategy_command(strategy_name: str, cmd: list[str]) -> bool:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=900,  # 15 minutes total timeout
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    success = result.returncode == 0
    if success:
        print(f"✅ Strategy '{strategy_name}' tests passed!")
    else:
        print(f"❌ Strategy '{strategy_name}' tests failed!")
    return success


def _strategy_matches_changed_files(
    strategy: Dict[str, object],
    changed_files: Set[str],
) -> bool:
    trigger_files = strategy.get("trigger_files", [])
    if not isinstance(trigger_files, list):
        return False
    for trigger_pattern in trigger_files:
        if not isinstance(trigger_pattern, str):
            continue
        if any(_matches_trigger_pattern(trigger_pattern, changed_file) for changed_file in changed_files):
            return True
    return False


def _matches_trigger_pattern(trigger_pattern: str, changed_file: str) -> bool:
    if "*" in trigger_pattern:
        return Path(changed_file).match(trigger_pattern)
    return changed_file.startswith(trigger_pattern)


def _append_python_strategy_if_needed(
    matched_strategies: List[str],
    changed_files: Set[str],
) -> None:
    if any(path.endswith(".py") for path in changed_files) and "python_files" not in matched_strategies:
        matched_strategies.append("python_files")


def _run_pre_checks(strategy: Dict[str, object]) -> bool:
    pre_checks = strategy.get("pre_check")
    if not isinstance(pre_checks, list):
        return True
    print("🔍 Running pre-check commands...")
    for cmd in pre_checks:
        if not isinstance(cmd, str):
            continue
        print(f"  Running: {cmd}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception as exc:
            print(f"❌ Error running pre-check: {exc}")
            return False
        if result.returncode != 0:
            print(f"❌ Pre-check failed: {cmd}")
            print("   " + (result.stderr or "<no stderr>"))
            return False
        print(f"  ✅ {cmd} passed")
    return True


def _build_pytest_command(
    strategy: Dict[str, object],
    *,
    coverage: bool,
) -> list[str]:
    cmd = ["python3", "-m", "pytest"]
    test_paths = strategy.get("test_paths", [])
    if isinstance(test_paths, list):
        cmd.extend(str(path) for path in test_paths)
    cmd.extend(["-v", "--tb=short", "-x", "--timeout=300"])
    if coverage:
        cmd.extend(["--cov=src/bioetl/", "--cov-report=term-missing"])
    return cmd


def run_all_matched_strategies(changed_files: Set[str], coverage: bool = False) -> bool:
    """Run all test strategies matched to changed files."""
    
    if not changed_files:
        print("⚠️  No changed files detected. Running default test suite.")
        # Run a reasonable default set
        return run_tests_for_strategy("python_files", coverage)
    
    print(f"🔍 Detected {len(changed_files)} changed files:")
    for f in sorted(changed_files):
        print(f"  • {f}")
    
    matched_strategies = match_files_to_strategy(changed_files)
    
    if not matched_strategies:
        print("⚠️  No specific test strategies matched. Running default tests.")
        return run_tests_for_strategy("python_files", coverage)
    
    print(f"🎯 Matched {len(matched_strategies)} test strategies:")
    for strategy_name in matched_strategies:
        strategy = TEST_SELECTION_STRATEGY[strategy_name]
        print(f"  • {strategy_name}: {strategy['description']}")
    
    all_passed = True
    
    for strategy_name in matched_strategies:
        success = run_tests_for_strategy(strategy_name, coverage)
        if not success:
            all_passed = False
            # Don't stop on failure - run all matched strategies
    
    return all_passed


def list_available_strategies():
    """List all available test selection strategies."""
    
    print("Available Test Selection Strategies:")
    print("=" * 60)
    
    for name, strategy in TEST_SELECTION_STRATEGY.items():
        print(f"\n📋 {name}")
        print(f"   Description: {strategy['description']}")
        print(f"   Trigger files: {', '.join(strategy['trigger_files'])}")
        print(f"   Test paths: {', '.join(strategy['test_paths'])}")
        if "pre_check" in strategy:
            print(f"   Pre-checks: {', '.join(strategy['pre_check'])}")


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="Test Selection Strategy - Run appropriate tests based on file changes"
    )
    
    parser.add_argument(
        "--git-target",
        default="HEAD",
        help="Git target for diff (default: HEAD)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage analysis"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available test selection strategies"
    )
    
    parser.add_argument(
        "--manual-files",
        nargs="+",
        help="Manually specify changed files instead of git diff"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_available_strategies()
        return
    
    # Get changed files
    if args.manual_files:
        changed_files = set(args.manual_files)
    else:
        changed_files = detect_changed_files(args.git_target)
    
    # Run appropriate tests
    success = run_all_matched_strategies(changed_files, args.coverage)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All matched test strategies passed!")
    else:
        print("❌ Some test strategies failed!")
    
    print("\n🎯 NEXT STEPS:")
    if not success:
        print("1. Review test failures and fix issues")
        print("2. Run specific failed tests for faster feedback")
        print("3. Use --coverage to identify untested code")
    else:
        print("1. Commit changes with confidence")
        print("2. Consider running broader test suites")
        print("3. Update test documentation if needed")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
