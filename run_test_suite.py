#!/usr/bin/env python3
"""Test runner for AME-file_size_limits-001-TEST refactoring validation."""

import subprocess
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    """Run a command and capture stdout/stderr."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    return result.returncode, result.stdout, result.stderr

def parse_pytest_output(output: str) -> Dict[str, int]:
    """Parse pytest output to extract test counts."""
    counts = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
    
    # Look for summary line like "5 passed in 2.34s"
    patterns = [
        r"(\d+)\s+passed",
        r"(\d+)\s+failed",
        r"(\d+)\s+skipped",
        r"(\d+)\s+error",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            test_type = pattern.split(r"\s+")[1]
            counts[test_type] = int(match.group(1))
    
    return counts

def main():
    """Execute all tests and generate report."""
    repo_root = Path(__file__).parent
    reports_dir = repo_root / "reports" / "exemptions_refactoring"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Test configurations
    tests = [
        {
            "name": "Unit domain tests",
            "cmd": ["uv", "run", "python", "-m", "pytest", "tests/unit/domain/", "-v", "--tb=short"],
            "output_file": "01-test-unit-domain.log"
        },
        {
            "name": "Code metrics tests",
            "cmd": ["uv", "run", "python", "-m", "pytest", "tests/architecture/test_code_metrics.py::TestFileSizeLimits", "-v", "--tb=short"],
            "output_file": "02-test-code-metrics.log"
        },
        {
            "name": "Quality burndown priorities test",
            "cmd": ["uv", "run", "python", "-m", "pytest", "tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries", "-v", "--tb=short"],
            "output_file": "03-test-burndown-priorities.log"
        },
        {
            "name": "Quality debt and exemptions tests",
            "cmd": ["uv", "run", "python", "-m", "pytest", "tests/architecture/test_quality_debt_scorecard.py", "tests/architecture/test_quality_exemptions_registry.py", "-v", "--tb=short"],
            "output_file": "04-test-debt-exemptions.log"
        },
        {
            "name": "Quality exemptions script",
            "cmd": ["uv", "run", "python", "scripts/check_quality_exemptions.py", "--mode", "auto", "--growth-mode", "auto", "--trend-report", "off"],
            "output_file": "05-check-exemptions.log"
        },
        {
            "name": "MyPy type checking",
            "cmd": ["uv", "run", "python", "-m", "mypy", 
                    "src/bioetl/domain/composite/config_models.py",
                    "src/bioetl/domain/composite/config_schema.py",
                    "src/bioetl/domain/composite/config_validators.py",
                    "--strict"],
            "output_file": "06-mypy-check.log"
        }
    ]
    
    results = []
    
    for test_config in tests:
        print(f"\n{'='*70}")
        print(f"Running: {test_config['name']}")
        print(f"{'='*70}\n")
        
        returncode, stdout, stderr = run_command(test_config["cmd"])
        
        # Save output to file
        output_file = reports_dir / test_config["output_file"]
        with open(output_file, "w") as f:
            f.write(f"Command: {' '.join(test_config['cmd'])}\n")
            f.write(f"Return code: {returncode}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(stdout)
            f.write("\n\n=== STDERR ===\n")
            f.write(stderr)
        
        # Parse results
        is_pytest = "pytest" in test_config["cmd"]
        is_mypy = "mypy" in test_config["cmd"]
        
        test_result = {
            "name": test_config["name"],
            "cmd": " ".join(test_config["cmd"]),
            "returncode": returncode,
            "status": "PASS" if returncode == 0 else "FAIL",
            "output_file": str(output_file),
        }
        
        if is_pytest:
            counts = parse_pytest_output(stdout + stderr)
            test_result["counts"] = counts
        elif is_mypy:
            test_result["mypy_output"] = stdout + stderr
        
        results.append(test_result)
        print(f"Status: {test_result['status']}")
    
    # Generate comprehensive report
    report_file = reports_dir / "05-test-final-AME-file_size_limits-001-TEST.md"
    
    with open(report_file, "w") as f:
        f.write("# Test Report: AME-file_size_limits-001-TEST\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Phase:** Final\n")
        f.write(f"**Task:** AME-file_size_limits-001-TEST\n\n")
        
        f.write("## Summary\n\n")
        f.write("### Changes Tested\n")
        f.write("- `src/bioetl/domain/composite/config_models.py`\n")
        f.write("- `src/bioetl/domain/composite/config_schema.py`\n")
        f.write("- `src/bioetl/domain/composite/config_validators.py`\n\n")
        
        f.write("### Refactoring\n")
        f.write("- LayerColumnConfig/DataSchemaConfig extracted to new module\n")
        f.write("- Coercion helpers extracted\n")
        f.write("- Simplified CrossValidationConfig._validate\n\n")
        
        # Count totals
        total_passed = sum(r.get("counts", {}).get("passed", 0) for r in results if "counts" in r)
        total_failed = sum(r.get("counts", {}).get("failed", 0) for r in results if "counts" in r)
        total_skipped = sum(r.get("counts", {}).get("skipped", 0) for r in results if "counts" in r)
        total_error = sum(r.get("counts", {}).get("error", 0) for r in results if "counts" in r)
        test_failures = [r for r in results if r["status"] == "FAIL"]
        
        overall_status = "PASS" if not test_failures else "FAIL"
        
        f.write(f"### Overall Status: **{overall_status}**\n\n")
        
        f.write("### Test Results Summary\n\n")
        f.write("| Test | Status | Passed | Failed | Skipped | Error |\n")
        f.write("|------|--------|--------|--------|---------|-------|\n")
        
        for result in results:
            if "counts" in result:
                counts = result["counts"]
                f.write(f"| {result['name']} | {result['status']} | "
                       f"{counts['passed']} | {counts['failed']} | "
                       f"{counts['skipped']} | {counts['error']} |\n")
            else:
                f.write(f"| {result['name']} | {result['status']} | N/A | N/A | N/A | N/A |\n")
        
        f.write("\n### Totals\n\n")
        f.write(f"- **Total Passed:** {total_passed}\n")
        f.write(f"- **Total Failed:** {total_failed}\n")
        f.write(f"- **Total Skipped:** {total_skipped}\n")
        f.write(f"- **Total Errors:** {total_error}\n\n")
        
        # Detailed results
        f.write("## Detailed Test Results\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"### Test {i}: {result['name']}\n\n")
            f.write(f"**Command:** `{result['cmd']}`\n\n")
            f.write(f"**Status:** `{result['status']}`\n\n")
            
            if "counts" in result:
                counts = result["counts"]
                f.write(f"**Results:**\n")
                f.write(f"- Passed: {counts['passed']}\n")
                f.write(f"- Failed: {counts['failed']}\n")
                f.write(f"- Skipped: {counts['skipped']}\n")
                f.write(f"- Errors: {counts['error']}\n\n")
            
            f.write(f"**Output file:** `{result['output_file']}`\n\n")
            
            if result['status'] == 'FAIL' and 'mypy_output' in result:
                f.write("**MyPy Output:**\n\n")
                f.write("```\n")
                f.write(result['mypy_output'][:1000])  # First 1000 chars
                f.write("\n```\n\n")
        
        # Failure details
        if test_failures:
            f.write("## Failures\n\n")
            for result in test_failures:
                f.write(f"### {result['name']}\n\n")
                f.write(f"Return code: {result['returncode']}\n\n")
                f.write(f"See output file: `{result['output_file']}`\n\n")
        
        f.write("## MyPy Type Checking\n\n")
        mypy_result = next((r for r in results if "mypy" in r["name"].lower()), None)
        if mypy_result:
            f.write(f"**Status:** {mypy_result['status']}\n\n")
            if mypy_result['status'] == 'PASS':
                f.write("✅ All type checks passed with --strict mode\n\n")
            f.write(f"See output file: `{mypy_result['output_file']}`\n\n")
        
        f.write("## Conclusion\n\n")
        f.write(f"**Final Status:** `{overall_status}`\n\n")
        
        if overall_status == "PASS":
            f.write("✅ All tests passed. The refactoring is complete and validated.\n")
        else:
            f.write("❌ Some tests failed. See detailed results above for debugging information.\n")
    
    print(f"\n{'='*70}")
    print(f"Report generated: {report_file}")
    print(f"{'='*70}\n")
    
    # Print summary
    print(f"\nOVERALL STATUS: {overall_status}")
    print(f"Tests Passed: {total_passed}")
    print(f"Tests Failed: {total_failed}")
    print(f"Tests Skipped: {total_skipped}")
    print(f"Tests Error: {total_error}")
    
    return 0 if overall_status == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
