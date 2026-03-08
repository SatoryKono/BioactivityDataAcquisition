@echo off
REM Test script for AME-file_size_limits-001-TEST
setlocal enabledelayedexpansion

cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2

if not exist reports\exemptions_refactoring mkdir reports\exemptions_refactoring

echo Test 1: Unit domain tests
uv run python -m pytest tests/unit/domain/ -v --tb=short > reports\exemptions_refactoring\01-test-unit-domain.log 2>&1
echo Test 1 completed. Output saved to reports\exemptions_refactoring\01-test-unit-domain.log

echo.
echo Test 2: Code metrics tests
uv run python -m pytest tests/architecture/test_code_metrics.py::TestFileSizeLimits -v --tb=short > reports\exemptions_refactoring\02-test-code-metrics.log 2>&1
echo Test 2 completed. Output saved to reports\exemptions_refactoring\02-test-code-metrics.log

echo.
echo Test 3: Quality burndown priorities test
uv run python -m pytest tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries -v --tb=short > reports\exemptions_refactoring\03-test-burndown-priorities.log 2>&1
echo Test 3 completed. Output saved to reports\exemptions_refactoring\03-test-burndown-priorities.log

echo.
echo Test 4: Quality debt and exemptions tests
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py -v --tb=short > reports\exemptions_refactoring\04-test-debt-exemptions.log 2>&1
echo Test 4 completed. Output saved to reports\exemptions_refactoring\04-test-debt-exemptions.log

echo.
echo Test 5: Quality exemptions script
uv run python scripts/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off > reports\exemptions_refactoring\05-check-exemptions.log 2>&1
echo Test 5 completed. Output saved to reports\exemptions_refactoring\05-check-exemptions.log

echo.
echo Test 6: mypy type checking
uv run python -m mypy src/bioetl/domain/composite/config_models.py src/bioetl/domain/composite/config_schema.py src/bioetl/domain/composite/config_validators.py --strict > reports\exemptions_refactoring\06-mypy-check.log 2>&1
echo Test 6 completed. Output saved to reports\exemptions_refactoring\06-mypy-check.log

echo.
echo All tests completed!
