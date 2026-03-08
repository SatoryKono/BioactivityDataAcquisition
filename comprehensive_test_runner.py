#!/usr/bin/env python3
"""
Comprehensive test suite runner for AME-file_size_limits-001-TEST refactoring.
Executes all required tests and generates a detailed report.
"""

import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

def change_to_repo():
    """Change to repository root."""
    repo_root = Path(__file__).parent
    os.chdir(repo_root)
    return repo_root

def ensure_output_dir(repo_root: Path) -> Path:
    """Ensure output directory exists."""
    output_dir = repo_root / "reports" / "exemptions_refactoring"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def run_test(name: str, cmd: List[str], output_dir: Path) -> Tuple[str, int, str]:
    """Run a single test command and save output."""
    output_file = output_dir / f"{name}.log"
    
    print(f"\n{'='*70}")
    print(f"Running: {name}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Save output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"Return code: {result.returncode}\n")
            f.write(f"Executed at: {datetime.now().isoformat()}\n\n")
            f.write("="*70 + "\n")
            f.write("STDOUT\n")
            f.write("="*70 + "\n")
            f.write(result.stdout)
            f.write("\n" + "="*70 + "\n")
            f.write("STDERR\n")
            f.write("="*70 + "\n")
            f.write(result.stderr)
        
        status_msg = f"✓ Return code: {result.returncode}"
        print(status_msg)
        
        return status_msg, result.returncode, str(output_file)
        
    except subprocess.TimeoutExpired:
        msg = "✗ TIMEOUT (>300s)"
        print(msg)
        with open(output_file, 'w') as f:
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write("TIMEOUT: Exceeded 300 seconds\n")
        return msg, -1, str(output_file)
        
    except Exception as e:
        msg = f"✗ ERROR: {e}"
        print(msg)
        with open(output_file, 'w') as f:
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"ERROR: {e}\n")
        return msg, -1, str(output_file)

def parse_pytest_log(log_file: Path) -> Dict[str, int]:
    """Extract test counts from pytest log."""
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return {'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0}
    
    counts = {'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0}
    
    patterns = [
        (r'(\d+)\s+passed', 'passed'),
        (r'(\d+)\s+failed', 'failed'),
        (r'(\d+)\s+skipped', 'skipped'),
        (r'(\d+)\s+error', 'error'),
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, content)
        if match:
            counts[key] = int(match.group(1))
    
    return counts

def read_log_excerpt(log_file: Path, lines_count: int = 20) -> str:
    """Read log file excerpt."""
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        return ''.join(lines[-lines_count:])
    except:
        return "Could not read file"

def generate_report(repo_root: Path, output_dir: Path, test_results: List[Dict]) -> Path:
    """Generate comprehensive markdown report."""
    report_file = output_dir / "05-test-final-AME-file_size_limits-001-TEST.md"
    
    # Calculate totals
    total_passed = sum(r.get('counts', {}).get('passed', 0) for r in test_results)
    total_failed = sum(r.get('counts', {}).get('failed', 0) for r in test_results)
    total_skipped = sum(r.get('counts', {}).get('skipped', 0) for r in test_results)
    total_error = sum(r.get('counts', {}).get('error', 0) for r in test_results)
    
    failed_tests = [r for r in test_results if r['returncode'] != 0]
    overall_status = "PASS" if not failed_tests else "FAIL"
    
    # Build report
    report_lines = []
    
    report_lines.append("# Test Report: AME-file_size_limits-001-TEST\n\n")
    report_lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"**Phase:** Final\n")
    report_lines.append(f"**Task:** AME-file_size_limits-001-TEST\n\n")
    
    report_lines.append("## Summary\n\n")
    report_lines.append("### Changes Tested\n")
    report_lines.append("- `src/bioetl/domain/composite/config_models.py`\n")
    report_lines.append("- `src/bioetl/domain/composite/config_schema.py`\n")
    report_lines.append("- `src/bioetl/domain/composite/config_validators.py`\n\n")
    
    report_lines.append("### Refactoring\n")
    report_lines.append("- LayerColumnConfig/DataSchemaConfig extracted to new module\n")
    report_lines.append("- Coercion helpers extracted\n")
    report_lines.append("- Simplified CrossValidationConfig._validate\n\n")
    
    report_lines.append(f"### Overall Status: **{overall_status}**\n\n")
    
    report_lines.append("### Test Results Summary\n\n")
    report_lines.append("| # | Test | Status | Return Code |\n")
    report_lines.append("|---|------|--------|-------------|\n")
    
    for i, result in enumerate(test_results, 1):
        status = "✅ PASS" if result['returncode'] == 0 else "❌ FAIL"
        report_lines.append(f"| {i} | {result['name']} | {status} | {result['returncode']} |\n")
    
    report_lines.append("\n### Test Counts Summary\n\n")
    report_lines.append("| Metric | Count |\n")
    report_lines.append("|--------|-------|\n")
    report_lines.append(f"| Total Passed | {total_passed} |\n")
    report_lines.append(f"| Total Failed | {total_failed} |\n")
    report_lines.append(f"| Total Skipped | {total_skipped} |\n")
    report_lines.append(f"| Total Errors | {total_error} |\n\n")
    
    report_lines.append("## Detailed Test Results\n\n")
    
    for i, result in enumerate(test_results, 1):
        report_lines.append(f"### Test {i}: {result['name']}\n\n")
        report_lines.append(f"**Command:** `{result['cmd']}`\n\n")
        report_lines.append(f"**Return Code:** `{result['returncode']}`\n\n")
        report_lines.append(f"**Status:** {'✅ PASS' if result['returncode'] == 0 else '❌ FAIL'}\n\n")
        
        if 'counts' in result and result['counts']['passed'] + result['counts']['failed'] + result['counts']['skipped'] + result['counts']['error'] > 0:
            counts = result['counts']
            report_lines.append(f"**Test Counts:**\n")
            report_lines.append(f"- Passed: {counts['passed']}\n")
            report_lines.append(f"- Failed: {counts['failed']}\n")
            report_lines.append(f"- Skipped: {counts['skipped']}\n")
            report_lines.append(f"- Errors: {counts['error']}\n\n")
        
        report_lines.append(f"**Output File:** `{result['output_file']}`\n\n")
    
    if failed_tests:
        report_lines.append("## Failures\n\n")
        for result in failed_tests:
            report_lines.append(f"### {result['name']}\n\n")
            report_lines.append(f"Return code: {result['returncode']}\n\n")
            log_path = Path(result['output_file'])
            if log_path.exists():
                excerpt = read_log_excerpt(log_path, 30)
                report_lines.append("**Error Output (last 30 lines):**\n\n")
                report_lines.append("```\n")
                report_lines.append(excerpt)
                report_lines.append("\n```\n\n")
    
    report_lines.append("## Conclusion\n\n")
    report_lines.append(f"**Final Status:** `{overall_status}`\n\n")
    
    if overall_status == "PASS":
        report_lines.append("✅ **All tests passed.** The refactoring is complete and validated.\n")
    else:
        report_lines.append("❌ **Some tests failed.** See detailed results above for debugging information.\n")
    
    # Write report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    
    return report_file

def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("COMPREHENSIVE TEST SUITE: AME-file_size_limits-001-TEST")
    print("="*70)
    
    # Setup
    repo_root = change_to_repo()
    output_dir = ensure_output_dir(repo_root)
    
    print(f"\nRepository: {repo_root}")
    print(f"Output directory: {output_dir}")
    
    # Define tests
    tests = [
        {
            "name": "01-test-unit-domain",
            "label": "Unit domain tests",
            "cmd": [sys.executable, "-m", "pytest", "tests/unit/domain/", "-v", "--tb=short"]
        },
        {
            "name": "02-test-code-metrics",
            "label": "Code metrics tests",
            "cmd": [sys.executable, "-m", "pytest", "tests/architecture/test_code_metrics.py::TestFileSizeLimits", "-v", "--tb=short"]
        },
        {
            "name": "03-test-burndown-priorities",
            "label": "Quality burndown priorities",
            "cmd": [sys.executable, "-m", "pytest", "tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries", "-v", "--tb=short"]
        },
        {
            "name": "04-test-debt-exemptions",
            "label": "Quality debt and exemptions",
            "cmd": [sys.executable, "-m", "pytest", "tests/architecture/test_quality_debt_scorecard.py", "tests/architecture/test_quality_exemptions_registry.py", "-v", "--tb=short"]
        },
        {
            "name": "05-check-exemptions",
            "label": "Quality exemptions script",
            "cmd": [sys.executable, "scripts/check_quality_exemptions.py", "--mode", "auto", "--growth-mode", "auto", "--trend-report", "off"]
        },
        {
            "name": "06-mypy-check",
            "label": "MyPy type checking",
            "cmd": [sys.executable, "-m", "mypy", 
                    "src/bioetl/domain/composite/config_models.py",
                    "src/bioetl/domain/composite/config_schema.py",
                    "src/bioetl/domain/composite/config_validators.py",
                    "--strict"]
        }
    ]
    
    # Run tests
    test_results = []
    
    for test in tests:
        status_msg, returncode, output_file = run_test(
            test["name"],
            test["cmd"],
            output_dir
        )
        
        result = {
            "name": test["label"],
            "cmd": " ".join(test["cmd"]),
            "returncode": returncode,
            "output_file": output_file
        }
        
        # For pytest tests, parse counts
        if "pytest" in test["cmd"]:
            counts = parse_pytest_log(Path(output_file))
            result["counts"] = counts
        
        test_results.append(result)
    
    # Generate report
    print(f"\n{'='*70}")
    print("Generating comprehensive report...")
    print(f"{'='*70}\n")
    
    report_file = generate_report(repo_root, output_dir, test_results)
    
    # Summary
    failed_tests = [r for r in test_results if r['returncode'] != 0]
    overall_status = "PASS" if not failed_tests else "FAIL"
    
    total_passed = sum(r.get('counts', {}).get('passed', 0) for r in test_results)
    total_failed = sum(r.get('counts', {}).get('failed', 0) for r in test_results)
    
    print(f"\n{'='*70}")
    print("TEST SUITE COMPLETE")
    print(f"{'='*70}\n")
    print(f"Overall Status: {overall_status}")
    print(f"Total Tests Passed: {total_passed}")
    print(f"Total Tests Failed: {total_failed}")
    print(f"Report: {report_file}\n")
    
    return 0 if overall_status == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
