@echo off
REM Test execution script for AME-file_size_limits-001-TEST
REM This script runs all required tests and collects output

setlocal enabledelayedexpansion

cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2

REM Ensure output directory exists
if not exist reports\exemptions_refactoring (
    mkdir reports\exemptions_refactoring
)

REM Test 1: Unit domain tests
echo ============================================================
echo Test 1 of 6: Unit domain tests
echo ============================================================
echo Running: python -m pytest tests/unit/domain/ -v --tb=short
python -m pytest tests/unit/domain/ -v --tb=short > "reports\exemptions_refactoring\01-test-unit-domain.log" 2>&1
set "TEST1_RC=!ERRORLEVEL!"
echo Return code: !TEST1_RC!
echo.

REM Test 2: Code metrics tests  
echo ============================================================
echo Test 2 of 6: Code metrics tests
echo ============================================================
echo Running: python -m pytest tests/architecture/test_code_metrics.py::TestFileSizeLimits -v --tb=short
python -m pytest tests/architecture/test_code_metrics.py::TestFileSizeLimits -v --tb=short > "reports\exemptions_refactoring\02-test-code-metrics.log" 2>&1
set "TEST2_RC=!ERRORLEVEL!"
echo Return code: !TEST2_RC!
echo.

REM Test 3: Quality burndown priorities test
echo ============================================================
echo Test 3 of 6: Quality burndown priorities test
echo ============================================================
echo Running: python -m pytest tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries -v --tb=short
python -m pytest tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries -v --tb=short > "reports\exemptions_refactoring\03-test-burndown-priorities.log" 2>&1
set "TEST3_RC=!ERRORLEVEL!"
echo Return code: !TEST3_RC!
echo.

REM Test 4: Quality debt and exemptions tests
echo ============================================================
echo Test 4 of 6: Quality debt and exemptions tests
echo ============================================================
echo Running: python -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py -v --tb=short
python -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py -v --tb=short > "reports\exemptions_refactoring\04-test-debt-exemptions.log" 2>&1
set "TEST4_RC=!ERRORLEVEL!"
echo Return code: !TEST4_RC!
echo.

REM Test 5: Quality exemptions script
echo ============================================================
echo Test 5 of 6: Quality exemptions script
echo ============================================================
echo Running: python scripts/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off
python scripts/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off > "reports\exemptions_refactoring\05-check-exemptions.log" 2>&1
set "TEST5_RC=!ERRORLEVEL!"
echo Return code: !TEST5_RC!
echo.

REM Test 6: MyPy type checking
echo ============================================================
echo Test 6 of 6: MyPy type checking
echo ============================================================
echo Running: python -m mypy src/bioetl/domain/composite/config_models.py src/bioetl/domain/composite/config_schema.py src/bioetl/domain/composite/config_validators.py --strict
python -m mypy src/bioetl/domain/composite/config_models.py src/bioetl/domain/composite/config_schema.py src/bioetl/domain/composite/config_validators.py --strict > "reports\exemptions_refactoring\06-mypy-check.log" 2>&1
set "TEST6_RC=!ERRORLEVEL!"
echo Return code: !TEST6_RC!
echo.

REM Generate final report using Python
echo ============================================================
echo Generating comprehensive report
echo ============================================================

python -c "
import os
import sys
from datetime import datetime
from pathlib import Path
import re

def count_pytest_results(log_file):
    '''Extract test counts from pytest log'''
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
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

def read_log(filename):
    '''Read log file safely'''
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except:
        return 'Could not read file'

# Test results
test_results = [
    ('01-test-unit-domain.log', 'Unit domain tests', $TEST1_RC),
    ('02-test-code-metrics.log', 'Code metrics tests', $TEST2_RC),
    ('03-test-burndown-priorities.log', 'Quality burndown priorities', $TEST3_RC),
    ('04-test-debt-exemptions.log', 'Quality debt and exemptions', $TEST4_RC),
    ('05-check-exemptions.log', 'Quality exemptions script', $TEST5_RC),
    ('06-mypy-check.log', 'MyPy type checking', $TEST6_RC),
]

report_dir = Path('reports/exemptions_refactoring')
report_file = report_dir / '05-test-final-AME-file_size_limits-001-TEST.md'

# Calculate totals
total_passed = 0
total_failed = 0
total_skipped = 0
total_error = 0

failed_tests = []

for log_file, test_name, rc in test_results:
    log_path = report_dir / log_file
    if log_path.exists():
        counts = count_pytest_results(log_path)
        total_passed += counts['passed']
        total_failed += counts['failed']
        total_skipped += counts['skipped']
        total_error += counts['error']
        if rc != 0:
            failed_tests.append((test_name, log_file, rc))

overall_status = 'PASS' if not failed_tests and sum(r[2] for r in test_results) == 0 else 'FAIL'

# Build report
report = []
report.append('# Test Report: AME-file_size_limits-001-TEST\n')
report.append(f'**Date:** {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\n')
report.append('**Phase:** Final\n')
report.append('**Task:** AME-file_size_limits-001-TEST\n\n')

report.append('## Summary\n\n')
report.append('### Changes Tested\n')
report.append('- `src/bioetl/domain/composite/config_models.py`\n')
report.append('- `src/bioetl/domain/composite/config_schema.py`\n')
report.append('- `src/bioetl/domain/composite/config_validators.py`\n\n')

report.append('### Refactoring\n')
report.append('- LayerColumnConfig/DataSchemaConfig extracted to new module\n')
report.append('- Coercion helpers extracted\n')
report.append('- Simplified CrossValidationConfig._validate\n\n')

report.append(f'### Overall Status: **{overall_status}**\n\n')

report.append('### Test Results Summary\n\n')
report.append('| Test | Status | Return Code |\n')
report.append('|------|--------|-------------|\n')

for log_file, test_name, rc in test_results:
    status = 'PASS' if rc == 0 else 'FAIL'
    report.append(f'| {test_name} | {status} | {rc} |\n')

report.append('\n### Totals\n\n')
report.append(f'- **Total Passed:** {total_passed}\n')
report.append(f'- **Total Failed:** {total_failed}\n')
report.append(f'- **Total Skipped:** {total_skipped}\n')
report.append(f'- **Total Errors:** {total_error}\n\n')

report.append('## Detailed Test Results\n\n')

for i, (log_file, test_name, rc) in enumerate(test_results, 1):
    report.append(f'### Test {i}: {test_name}\n\n')
    report.append(f'**Log File:** `{log_file}`\n')
    report.append(f'**Return Code:** `{rc}`\n')
    report.append(f'**Status:** {'✅ PASS' if rc == 0 else '❌ FAIL'}\n\n')
    
    log_path = report_dir / log_file
    if log_path.exists():
        log_content = read_log(log_path)
        counts = count_pytest_results(log_path)
        if counts['passed'] + counts['failed'] + counts['skipped'] + counts['error'] > 0:
            report.append(f'**Results:** {counts[\"passed\"]} passed, {counts[\"failed\"]} failed, {counts[\"skipped\"]} skipped, {counts[\"error\"]} errors\n\n')
        
        # Show first and last 30 lines of output
        lines = log_content.split('\n')
        report.append('**Output (first 20 lines):**\n\n')
        report.append('```\n')
        report.append('\n'.join(lines[:20]))
        report.append('\n```\n\n')
        
        if len(lines) > 40:
            report.append('**Output (last 20 lines):**\n\n')
            report.append('```\n')
            report.append('\n'.join(lines[-20:]))
            report.append('\n```\n\n')

if failed_tests:
    report.append('## Failures\n\n')
    for test_name, log_file, rc in failed_tests:
        report.append(f'### {test_name}\n\n')
        report.append(f'Return code: {rc}\n\n')
        log_path = report_dir / log_file
        if log_path.exists():
            log_content = read_log(log_path)
            lines = log_content.split('\n')
            report.append('**Error output (last 30 lines):**\n\n')
            report.append('```\n')
            report.append('\n'.join(lines[-30:]))
            report.append('\n```\n\n')

report.append('## Conclusion\n\n')
report.append(f'**Final Status:** `{overall_status}`\n\n')

if overall_status == 'PASS':
    report.append('✅ All tests passed. The refactoring is complete and validated.\n')
else:
    report.append('❌ Some tests failed. See detailed results above for debugging information.\n')

# Write report
with open(report_file, 'w') as f:
    f.writelines(report)

print(f'Report generated: {report_file}')
print(f'Overall Status: {overall_status}')
"

echo.
echo ============================================================
echo Test suite completed!
echo ============================================================
echo Final report: reports\exemptions_refactoring\05-test-final-AME-file_size_limits-001-TEST.md
echo.

endlocal
