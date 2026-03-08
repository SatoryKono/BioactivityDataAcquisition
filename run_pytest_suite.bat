@echo off
setlocal enabledelayedexpansion

REM Create output directory
if not exist "reports\exemptions_refactoring" mkdir "reports\exemptions_refactoring"

REM Initialize output file
(
echo ================================================================================
echo PYTEST OUTPUT SUMMARY - Exemptions Refactoring Test Suite
echo ================================================================================
echo Timestamp: %date% %time%
echo.
) > "reports\exemptions_refactoring\pytest-output.txt"

REM Run test 1
echo.
echo Running Test 1: Unit Domain Tests
echo. >> "reports\exemptions_refactoring\pytest-output.txt"
echo === TEST 1: Unit Domain Tests === >> "reports\exemptions_refactoring\pytest-output.txt"
echo. >> "reports\exemptions_refactoring\pytest-output.txt"
call uv run python -m pytest tests/unit/domain/ -v --tb=short >> "reports\exemptions_refactoring\pytest-output.txt" 2>&1

REM Run test 2
echo.
echo Running Test 2: Code Metrics - File Size Limits
echo. >> "reports\exemptions_refactoring\pytest-output.txt"
echo === TEST 2: Code Metrics - File Size Limits === >> "reports\exemptions_refactoring\pytest-output.txt"
echo. >> "reports\exemptions_refactoring\pytest-output.txt"
call uv run python -m pytest tests/architecture/test_code_metrics.py::TestFileSizeLimits -v --tb=short >> "reports\exemptions_refactoring\pytest-output.txt" 2>&1

REM Run test 3
echo.
echo Running Test 3: Quality Burndown Priorities
echo. >> "reports\exemptions_refactoring\pytest-output.txt"
echo === TEST 3: Quality Burndown Priorities === >> "reports\exemptions_refactoring\pytest-output.txt"
echo. >> "reports\exemptions_refactoring\pytest-output.txt"
call uv run python -m pytest tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries -v --tb=short >> "reports\exemptions_refactoring\pytest-output.txt" 2>&1

REM Run test 4
echo.
echo Running Test 4: Quality Debt Scorecard - Exemptions Registry
echo. >> "reports\exemptions_refactoring\pytest-output.txt"
echo === TEST 4: Quality Debt Scorecard - Exemptions Registry === >> "reports\exemptions_refactoring\pytest-output.txt"
echo. >> "reports\exemptions_refactoring\pytest-output.txt"
call uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py -v --tb=short >> "reports\exemptions_refactoring\pytest-output.txt" 2>&1

echo.
echo All tests completed. Output saved to: reports\exemptions_refactoring\pytest-output.txt
pause
