@echo off
REM Comprehensive test runner for AME-file_size_limits-001-TEST
setlocal enabledelayedexpansion

cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2

REM Create output directory
if not exist reports\exemptions_refactoring mkdir reports\exemptions_refactoring

REM Run all tests and capture outputs
echo ========================================
echo Test 1: Unit domain tests
echo ========================================
uv run python -m pytest tests/unit/domain/ -v --tb=short > reports\exemptions_refactoring\01-test-unit-domain.log 2>&1
set "TEST1_RETURN=%ERRORLEVEL%"
echo Return code: !TEST1_RETURN!

echo.
echo ========================================
echo Test 2: Code metrics tests
echo ========================================
uv run python -m pytest tests/architecture/test_code_metrics.py::TestFileSizeLimits -v --tb=short > reports\exemptions_refactoring\02-test-code-metrics.log 2>&1
set "TEST2_RETURN=%ERRORLEVEL%"
echo Return code: !TEST2_RETURN!

echo.
echo ========================================
echo Test 3: Quality burndown priorities test
echo ========================================
uv run python -m pytest tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries -v --tb=short > reports\exemptions_refactoring\03-test-burndown-priorities.log 2>&1
set "TEST3_RETURN=%ERRORLEVEL%"
echo Return code: !TEST3_RETURN!

echo.
echo ========================================
echo Test 4: Quality debt and exemptions tests
echo ========================================
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py -v --tb=short > reports\exemptions_refactoring\04-test-debt-exemptions.log 2>&1
set "TEST4_RETURN=%ERRORLEVEL%"
echo Return code: !TEST4_RETURN!

echo.
echo ========================================
echo Test 5: Quality exemptions script
echo ========================================
uv run python scripts/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off > reports\exemptions_refactoring\05-check-exemptions.log 2>&1
set "TEST5_RETURN=%ERRORLEVEL%"
echo Return code: !TEST5_RETURN!

echo.
echo ========================================
echo Test 6: MyPy type checking
echo ========================================
uv run python -m mypy src/bioetl/domain/composite/config_models.py src/bioetl/domain/composite/config_schema.py src/bioetl/domain/composite/config_validators.py --strict > reports\exemptions_refactoring\06-mypy-check.log 2>&1
set "TEST6_RETURN=%ERRORLEVEL%"
echo Return code: !TEST6_RETURN!

echo.
echo ========================================
echo All tests completed!
echo ========================================

REM Create Python script to generate the final report
cd reports\exemptions_refactoring
python -c ^
"^
import sys^
import os^
from datetime import datetime^
^
def parse_pytest_log(filename):^
    with open(filename, 'r') as f:^
        content = f.read()^
    counts = {'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0}^
    import re^
    if 'passed' in content:^
        m = re.search(r'(\d+)\s+passed', content)^
        if m: counts['passed'] = int(m.group(1))^
    if 'failed' in content:^
        m = re.search(r'(\d+)\s+failed', content)^
        if m: counts['failed'] = int(m.group(1))^
    if 'skipped' in content:^
        m = re.search(r'(\d+)\s+skipped', content)^
        if m: counts['skipped'] = int(m.group(1))^
    return counts^
^
results = [^
    ('01-test-unit-domain.log', 'Unit domain tests', !TEST1_RETURN!),^
    ('02-test-code-metrics.log', 'Code metrics tests', !TEST2_RETURN!),^
    ('03-test-burndown-priorities.log', 'Quality burndown priorities', !TEST3_RETURN!),^
    ('04-test-debt-exemptions.log', 'Quality debt and exemptions', !TEST4_RETURN!),^
    ('05-check-exemptions.log', 'Quality exemptions script', !TEST5_RETURN!),^
    ('06-mypy-check.log', 'MyPy type checking', !TEST6_RETURN!),^
]^
^
with open('05-test-final-AME-file_size_limits-001-TEST.md', 'w') as f:^
    f.write('# Test Report: AME-file_size_limits-001-TEST\n\n')^
    f.write(f'**Date:** {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\n')^
    f.write(f'**Phase:** Final\n')^
    f.write(f'**Task:** AME-file_size_limits-001-TEST\n\n')^
    f.write('## Summary\n\n')^
    f.write('### Changes Tested\n')^
    f.write('- `src/bioetl/domain/composite/config_models.py`\n')^
    f.write('- `src/bioetl/domain/composite/config_schema.py`\n')^
    f.write('- `src/bioetl/domain/composite/config_validators.py`\n\n')^
    f.write('### Refactoring\n')^
    f.write('- LayerColumnConfig/DataSchemaConfig extracted to new module\n')^
    f.write('- Coercion helpers extracted\n')^
    f.write('- Simplified CrossValidationConfig._validate\n\n')^
"
