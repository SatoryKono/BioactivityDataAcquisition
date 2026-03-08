@echo off
setlocal enabledelayedexpansion

REM Run Tests and Save to pytest-output.txt
cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2

REM Append test results to the existing file
(
    echo.
    echo ================================================================================
    echo PYTEST EXECUTION - %date% %time%
    echo ================================================================================
    echo.
) >> reports\exemptions_refactoring\pytest-output.txt

REM Test 1
echo Running Test 1: Unit Domain Tests
echo === TEST 1: Unit Domain Tests === >> reports\exemptions_refactoring\pytest-output.txt
uv run python -m pytest tests/unit/domain/ -v --tb=short >> reports\exemptions_refactoring\pytest-output.txt 2>&1
echo Test 1 complete >> reports\exemptions_refactoring\pytest-output.txt
echo.

REM Test 2
echo Running Test 2: Code Metrics - File Size Limits
echo === TEST 2: Code Metrics - File Size Limits === >> reports\exemptions_refactoring\pytest-output.txt
uv run python -m pytest tests/architecture/test_code_metrics.py::TestFileSizeLimits -v --tb=short >> reports\exemptions_refactoring\pytest-output.txt 2>&1
echo Test 2 complete >> reports\exemptions_refactoring\pytest-output.txt
echo.

REM Test 3
echo Running Test 3: Quality Burndown Priorities
echo === TEST 3: Quality Burndown Priorities === >> reports\exemptions_refactoring\pytest-output.txt
uv run python -m pytest tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries -v --tb=short >> reports\exemptions_refactoring\pytest-output.txt 2>&1
echo Test 3 complete >> reports\exemptions_refactoring\pytest-output.txt
echo.

REM Test 4
echo Running Test 4: Quality Debt Scorecard - Exemptions Registry
echo === TEST 4: Quality Debt Scorecard - Exemptions Registry === >> reports\exemptions_refactoring\pytest-output.txt
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py -v --tb=short >> reports\exemptions_refactoring\pytest-output.txt 2>&1
echo Test 4 complete >> reports\exemptions_refactoring\pytest-output.txt
echo.

echo.
echo ================================================================================
echo All tests completed!
echo Output saved to: reports\exemptions_refactoring\pytest-output.txt
echo ================================================================================
echo.
pause
