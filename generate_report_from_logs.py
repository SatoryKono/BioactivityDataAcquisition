#!/usr/bin/env python3
"""Generate comprehensive report from existing test logs."""

import re
from pathlib import Path
from datetime import datetime

def parse_pytest_log(log_file):
    """Extract test counts from pytest log."""
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return None
    
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

def read_log_lines(log_file, num_lines=30):
    """Read last N lines from log file."""
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        return ''.join(lines[-num_lines:]) if lines else "Log file empty"
    except:
        return "Could not read log file"

def get_return_code(log_file):
    """Extract return code from log file."""
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
        match = re.search(r'Return code: (\d+)', first_line)
        if match:
            return int(match.group(1))
    except:
        pass
    return -1

def main():
    """Generate report from existing logs."""
    reports_dir = Path("reports/exemptions_refactoring")
    
    if not reports_dir.exists():
        print("reports/exemptions_refactoring does not exist!")
        return
    
    # Map log files to test info
    test_logs = [
        ("01-test-unit-domain.log", "Unit domain tests"),
        ("02-test-code-metrics.log", "Code metrics tests"),
        ("03-test-burndown-priorities.log", "Quality burndown priorities"),
        ("04-test-debt-exemptions.log", "Quality debt and exemptions"),
        ("05-check-exemptions.log", "Quality exemptions script"),
        ("06-mypy-check.log", "MyPy type checking"),
    ]
    
    # Parse results
    results = []
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_error = 0
    failed_tests = []
    
    for log_file, test_name in test_logs:
        log_path = reports_dir / log_file
        
        if not log_path.exists():
            print(f"Warning: {log_file} not found")
            results.append({
                'name': test_name,
                'log_file': log_file,
                'rc': -1,
                'counts': None,
                'exists': False
            })
            failed_tests.append((test_name, log_file, -1))
            continue
        
        rc = get_return_code(log_path)
        counts = parse_pytest_log(log_path) if "pytest" in log_file or "mypy" not in log_file else None
        
        results.append({
            'name': test_name,
            'log_file': log_file,
            'rc': rc,
            'counts': counts,
            'exists': True
        })
        
        if counts:
            total_passed += counts['passed']
            total_failed += counts['failed']
            total_skipped += counts['skipped']
            total_error += counts['error']
        
        if rc != 0:
            failed_tests.append((test_name, log_file, rc))
    
    overall_status = "PASS" if not failed_tests else "FAIL"
    
    # Generate report
    report_file = reports_dir / "05-test-final-AME-file_size_limits-001-TEST.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
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
        
        f.write(f"### Overall Status: **{overall_status}**\n\n")
        
        f.write("### Test Results Summary\n\n")
        f.write("| # | Test | Status | Return Code |\n")
        f.write("|---|------|--------|-------------|\n")
        
        for i, result in enumerate(results, 1):
            status = "✅ PASS" if result['rc'] == 0 else "❌ FAIL"
            f.write(f"| {i} | {result['name']} | {status} | {result['rc']} |\n")
        
        f.write("\n### Test Counts Summary\n\n")
        f.write("| Metric | Count |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Total Passed | {total_passed} |\n")
        f.write(f"| Total Failed | {total_failed} |\n")
        f.write(f"| Total Skipped | {total_skipped} |\n")
        f.write(f"| Total Errors | {total_error} |\n\n")
        
        f.write("## Detailed Test Results\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"### Test {i}: {result['name']}\n\n")
            
            if not result['exists']:
                f.write(f"**Status:** ⚠️ Log file not found\n\n")
                f.write(f"**Log File:** `{result['log_file']}`\n\n")
                continue
            
            f.write(f"**Return Code:** `{result['rc']}`\n\n")
            f.write(f"**Status:** {'✅ PASS' if result['rc'] == 0 else '❌ FAIL'}\n\n")
            
            if result['counts']:
                counts = result['counts']
                if counts['passed'] + counts['failed'] + counts['skipped'] + counts['error'] > 0:
                    f.write(f"**Test Counts:**\n")
                    f.write(f"- Passed: {counts['passed']}\n")
                    f.write(f"- Failed: {counts['failed']}\n")
                    f.write(f"- Skipped: {counts['skipped']}\n")
                    f.write(f"- Errors: {counts['error']}\n\n")
            
            f.write(f"**Log File:** `{result['log_file']}`\n\n")
        
        if failed_tests:
            f.write("## Failures\n\n")
            for test_name, log_file, rc in failed_tests:
                f.write(f"### {test_name}\n\n")
                f.write(f"Return code: {rc}\n\n")
                log_path = reports_dir / log_file
                if log_path.exists():
                    excerpt = read_log_lines(log_path, 30)
                    f.write("**Error Output (last 30 lines):**\n\n")
                    f.write("```\n")
                    f.write(excerpt)
                    f.write("\n```\n\n")
        
        f.write("## Conclusion\n\n")
        f.write(f"**Final Status:** `{overall_status}`\n\n")
        
        if overall_status == "PASS":
            f.write("✅ **All tests passed.** The refactoring is complete and validated.\n")
        else:
            f.write("❌ **Some tests failed or logs missing.** See detailed results above for debugging information.\n")
    
    print(f"Report generated: {report_file}")
    print(f"Overall Status: {overall_status}")
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_failed}")

if __name__ == "__main__":
    main()
