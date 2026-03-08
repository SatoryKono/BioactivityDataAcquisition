#!/usr/bin/env python3
"""Simple test runner to execute all tests sequentially."""

import subprocess
import os
from pathlib import Path

os.chdir(Path(__file__).parent)

# Create output directory
Path("reports/exemptions_refactoring").mkdir(parents=True, exist_ok=True)

tests = [
    ("Unit domain tests", 
     ["python", "-m", "pytest", "tests/unit/domain/", "-v", "--tb=short"],
     "reports/exemptions_refactoring/01-test-unit-domain.log"),
    
    ("Code metrics tests",
     ["python", "-m", "pytest", "tests/architecture/test_code_metrics.py::TestFileSizeLimits", "-v", "--tb=short"],
     "reports/exemptions_refactoring/02-test-code-metrics.log"),
    
    ("Quality burndown priorities",
     ["python", "-m", "pytest", "tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries", "-v", "--tb=short"],
     "reports/exemptions_refactoring/03-test-burndown-priorities.log"),
    
    ("Quality debt and exemptions",
     ["python", "-m", "pytest", "tests/architecture/test_quality_debt_scorecard.py", "tests/architecture/test_quality_exemptions_registry.py", "-v", "--tb=short"],
     "reports/exemptions_refactoring/04-test-debt-exemptions.log"),
    
    ("Quality exemptions script",
     ["python", "scripts/check_quality_exemptions.py", "--mode", "auto", "--growth-mode", "auto", "--trend-report", "off"],
     "reports/exemptions_refactoring/05-check-exemptions.log"),
    
    ("MyPy type checking",
     ["python", "-m", "mypy", 
      "src/bioetl/domain/composite/config_models.py",
      "src/bioetl/domain/composite/config_schema.py",
      "src/bioetl/domain/composite/config_validators.py",
      "--strict"],
     "reports/exemptions_refactoring/06-mypy-check.log"),
]

print("Running comprehensive test suite...")
print("=" * 70)

for test_name, cmd, output_file in tests:
    print(f"\nRunning: {test_name}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        with open(output_file, 'w') as f:
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"Return code: {result.returncode}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout)
            f.write("\n\n=== STDERR ===\n")
            f.write(result.stderr)
        
        print(f"✓ Completed (return code: {result.returncode})")
        print(f"  Output saved to: {output_file}")
        
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout (exceeded 300 seconds)")
        with open(output_file, 'w') as f:
            f.write(f"Command: {' '.join(cmd)}\nTIMEOUT: Exceeded 300 seconds\n")
    except Exception as e:
        print(f"✗ Error: {e}")
        with open(output_file, 'w') as f:
            f.write(f"Command: {' '.join(cmd)}\nERROR: {e}\n")

print("\n" + "=" * 70)
print("All tests completed. Now generating final report...")
