#!/usr/bin/env python
"""Execute exemptions refactoring pytest suite and capture output."""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_test(test_name, cmd):
    """Run a single test command."""
    print(f"\nRunning: {test_name}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def main():
    """Execute pytest suite and save output."""
    
    # Create output directory
    output_dir = Path("reports/exemptions_refactoring")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "pytest-output.txt"
    
    # Test commands to run
    tests = [
        ("Unit Domain Tests", [
            "uv", "run", "python", "-m", "pytest", 
            "tests/unit/domain/", "-v", "--tb=short"
        ]),
        ("Code Metrics - File Size Limits", [
            "uv", "run", "python", "-m", "pytest", 
            "tests/architecture/test_code_metrics.py::TestFileSizeLimits", 
            "-v", "--tb=short"
        ]),
        ("Quality Burndown Priorities", [
            "uv", "run", "python", "-m", "pytest", 
            "tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries", 
            "-v", "--tb=short"
        ]),
        ("Quality Debt Scorecard & Exemptions Registry", [
            "uv", "run", "python", "-m", "pytest", 
            "tests/architecture/test_quality_debt_scorecard.py",
            "tests/architecture/test_quality_exemptions_registry.py",
            "-v", "--tb=short"
        ]),
    ]
    
    # Write header to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("PYTEST OUTPUT SUMMARY - Exemptions Refactoring Test Suite\n")
        f.write("=" * 80 + "\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Working directory: {Path.cwd()}\n\n")
    
    all_results = []
    
    # Run all tests
    for test_name, cmd in tests:
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")
        
        result = run_test(test_name, cmd)
        all_results.append((test_name, result))
        
        # Append output to file
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"TEST: {test_name}\n")
            f.write(f"{'='*70}\n")
            f.write(f"Command: {' '.join(cmd)}\n\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\nSTDERR:\n")
                f.write(result.stderr)
            f.write(f"\nReturn code: {result.returncode}\n")
        
        # Print stdout
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    
    # Parse summary statistics
    print(f"\n{'='*70}")
    print("FINAL TEST SUMMARY")
    print(f"{'='*70}\n")
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_errors = 0
    
    # Read final output file and parse
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract pytest summary lines
    print("Individual test results:")
    for line in content.split("\n"):
        if " passed" in line or " failed" in line or " error" in line or " skipped" in line:
            if "==" in line and ("passed" in line or "failed" in line):
                print(f"  {line.strip()}")
    
    print(f"\nFull output saved to: {output_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
