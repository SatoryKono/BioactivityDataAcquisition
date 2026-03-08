#!/usr/bin/env python3
"""Execute tests and generate report."""

import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime

def main():
    os.chdir(r'E:\g-drive\05_AI\github\BioactivityDataAcquisition2')
    
    # Create output directory
    reports_dir = Path("reports/exemptions_refactoring")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*70)
    print("STARTING TEST EXECUTION")
    print("="*70)
    
    tests = [
        {
            "cmd": ["python", "-m", "pytest", "tests/unit/domain/", "-v", "--tb=short"],
            "log": "01-test-unit-domain.log",
            "name": "Unit domain tests"
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/architecture/test_code_metrics.py::TestFileSizeLimits", "-v", "--tb=short"],
            "log": "02-test-code-metrics.log",
            "name": "Code metrics tests"
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries", "-v", "--tb=short"],
            "log": "03-test-burndown-priorities.log",
            "name": "Quality burndown priorities"
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/architecture/test_quality_debt_scorecard.py", "tests/architecture/test_quality_exemptions_registry.py", "-v", "--tb=short"],
            "log": "04-test-debt-exemptions.log",
            "name": "Quality debt and exemptions"
        },
        {
            "cmd": ["python", "scripts/check_quality_exemptions.py", "--mode", "auto", "--growth-mode", "auto", "--trend-report", "off"],
            "log": "05-check-exemptions.log",
            "name": "Quality exemptions script"
        },
        {
            "cmd": ["python", "-m", "mypy", 
                    "src/bioetl/domain/composite/config_models.py",
                    "src/bioetl/domain/composite/config_schema.py",
                    "src/bioetl/domain/composite/config_validators.py",
                    "--strict"],
            "log": "06-mypy-check.log",
            "name": "MyPy type checking"
        }
    ]
    
    results = []
    
    for i, test in enumerate(tests, 1):
        print(f"\n[{i}/{len(tests)}] {test['name']}")
        print(f"Command: {' '.join(test['cmd'])}")
        
        try:
            result = subprocess.run(
                test['cmd'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=r'E:\g-drive\05_AI\github\BioactivityDataAcquisition2'
            )
            
            # Save output
            log_path = reports_dir / test['log']
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"Return code: {result.returncode}\n\n")
                f.write("=== STDOUT ===\n")
                f.write(result.stdout)
                f.write("\n\n=== STDERR ===\n")
                f.write(result.stderr)
            
            results.append({
                'name': test['name'],
                'log': test['log'],
                'rc': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
            print(f"✓ Return code: {result.returncode}")
            
        except subprocess.TimeoutExpired:
            print(f"✗ TIMEOUT")
            log_path = reports_dir / test['log']
            with open(log_path, 'w') as f:
                f.write("TIMEOUT: Exceeded 300 seconds\n")
            results.append({
                'name': test['name'],
                'log': test['log'],
                'rc': -1,
                'stdout': 'TIMEOUT',
                'stderr': ''
            })
        except Exception as e:
            print(f"✗ ERROR: {e}")
            log_path = reports_dir / test['log']
            with open(log_path, 'w') as f:
                f.write(f"ERROR: {e}\n")
            results.append({
                'name': test['name'],
                'log': test['log'],
                'rc': -1,
                'stdout': '',
                'stderr': str(e)
            })
    
    # Generate report
    print("\n" + "="*70)
    print("GENERATING REPORT")
    print("="*70 + "\n")
    
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_error = 0
    failed_tests = []
    
    for result in results:
        # Parse pytest output
        content = result['stdout'] + result['stderr']
        
        if 'passed' in content:
            m = re.search(r'(\d+)\s+passed', content)
            if m: total_passed += int(m.group(1))
        
        if 'failed' in content:
            m = re.search(r'(\d+)\s+failed', content)
            if m: total_failed += int(m.group(1))
        
        if 'skipped' in content:
            m = re.search(r'(\d+)\s+skipped', content)
            if m: total_skipped += int(m.group(1))
        
        if result['rc'] != 0:
            failed_tests.append((result['name'], result['log'], result['rc']))
    
    overall_status = "PASS" if not failed_tests else "FAIL"
    
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
        f.write(f"| Total Skipped | {total_skipped} |\n\n")
        
        f.write("## Detailed Test Results\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"### Test {i}: {result['name']}\n\n")
            f.write(f"**Return Code:** `{result['rc']}`\n\n")
            f.write(f"**Status:** {'✅ PASS' if result['rc'] == 0 else '❌ FAIL'}\n\n")
            f.write(f"**Log File:** `{result['log']}`\n\n")
        
        if failed_tests:
            f.write("## Failures\n\n")
            for test_name, log_file, rc in failed_tests:
                f.write(f"### {test_name}\n\n")
                f.write(f"Return code: {rc}\n\n")
                log_path = reports_dir / log_file
                if log_path.exists():
                    try:
                        with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
                            lines = lf.readlines()
                        excerpt = ''.join(lines[-30:]) if lines else "Empty log"
                        f.write("**Error Output (last 30 lines):**\n\n")
                        f.write("```\n")
                        f.write(excerpt)
                        f.write("\n```\n\n")
                    except:
                        f.write("Could not read log file\n\n")
        
        f.write("## Conclusion\n\n")
        f.write(f"**Final Status:** `{overall_status}`\n\n")
        
        if overall_status == "PASS":
            f.write("✅ **All tests passed.** The refactoring is complete and validated.\n")
        else:
            f.write("❌ **Some tests failed.** See detailed results above for debugging information.\n")
    
    print(f"Report: {report_file}")
    print(f"Overall Status: {overall_status}")
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_failed}")
    print(f"Failed Tests: {len(failed_tests)}")

if __name__ == "__main__":
    main()
