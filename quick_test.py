#!/usr/bin/env python3
"""Direct test execution for refactoring validation."""

import subprocess
import os
from pathlib import Path

os.chdir(Path(__file__).parent)

# Create output directory
Path("reports/exemptions_refactoring").mkdir(parents=True, exist_ok=True)

# Test 1: Unit domain
print("="*70)
print("Test 1: Unit domain tests")
print("="*70)
result1 = subprocess.run(
    ["python", "-m", "pytest", "tests/unit/domain/", "-v", "--tb=short"],
    capture_output=True,
    text=True
)
with open("reports/exemptions_refactoring/01-test-unit-domain.log", "w") as f:
    f.write(f"Return code: {result1.returncode}\n\n=== STDOUT ===\n{result1.stdout}\n\n=== STDERR ===\n{result1.stderr}")
print(f"Return code: {result1.returncode}")

# Test 2: Code metrics
print("\n" + "="*70)
print("Test 2: Code metrics tests")
print("="*70)
result2 = subprocess.run(
    ["python", "-m", "pytest", "tests/architecture/test_code_metrics.py::TestFileSizeLimits", "-v", "--tb=short"],
    capture_output=True,
    text=True
)
with open("reports/exemptions_refactoring/02-test-code-metrics.log", "w") as f:
    f.write(f"Return code: {result2.returncode}\n\n=== STDOUT ===\n{result2.stdout}\n\n=== STDERR ===\n{result2.stderr}")
print(f"Return code: {result2.returncode}")

# Test 3: Burndown priorities
print("\n" + "="*70)
print("Test 3: Quality burndown priorities")
print("="*70)
result3 = subprocess.run(
    ["python", "-m", "pytest", "tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries", "-v", "--tb=short"],
    capture_output=True,
    text=True
)
with open("reports/exemptions_refactoring/03-test-burndown-priorities.log", "w") as f:
    f.write(f"Return code: {result3.returncode}\n\n=== STDOUT ===\n{result3.stdout}\n\n=== STDERR ===\n{result3.stderr}")
print(f"Return code: {result3.returncode}")

# Test 4: Debt and exemptions
print("\n" + "="*70)
print("Test 4: Quality debt and exemptions")
print("="*70)
result4 = subprocess.run(
    ["python", "-m", "pytest", "tests/architecture/test_quality_debt_scorecard.py", "tests/architecture/test_quality_exemptions_registry.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    timeout=300
)
with open("reports/exemptions_refactoring/04-test-debt-exemptions.log", "w") as f:
    f.write(f"Return code: {result4.returncode}\n\n=== STDOUT ===\n{result4.stdout}\n\n=== STDERR ===\n{result4.stderr}")
print(f"Return code: {result4.returncode}")

# Test 5: Exemptions script
print("\n" + "="*70)
print("Test 5: Quality exemptions script")
print("="*70)
result5 = subprocess.run(
    ["python", "scripts/check_quality_exemptions.py", "--mode", "auto", "--growth-mode", "auto", "--trend-report", "off"],
    capture_output=True,
    text=True,
    timeout=120
)
with open("reports/exemptions_refactoring/05-check-exemptions.log", "w") as f:
    f.write(f"Return code: {result5.returncode}\n\n=== STDOUT ===\n{result5.stdout}\n\n=== STDERR ===\n{result5.stderr}")
print(f"Return code: {result5.returncode}")

# Test 6: MyPy
print("\n" + "="*70)
print("Test 6: MyPy type checking")
print("="*70)
result6 = subprocess.run(
    ["python", "-m", "mypy", 
     "src/bioetl/domain/composite/config_models.py",
     "src/bioetl/domain/composite/config_schema.py",
     "src/bioetl/domain/composite/config_validators.py",
     "--strict"],
    capture_output=True,
    text=True,
    timeout=60
)
with open("reports/exemptions_refactoring/06-mypy-check.log", "w") as f:
    f.write(f"Return code: {result6.returncode}\n\n=== STDOUT ===\n{result6.stdout}\n\n=== STDERR ===\n{result6.stderr}")
print(f"Return code: {result6.returncode}")

print("\n" + "="*70)
print("All tests executed. Generating report...")
print("="*70)
