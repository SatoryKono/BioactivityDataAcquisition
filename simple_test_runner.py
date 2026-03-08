import subprocess
import sys
from pathlib import Path

# Setup
output_dir = Path("reports/exemptions_refactoring")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "pytest-output.txt"

# Test commands
tests = [
    ("Unit Domain Tests", "uv run python -m pytest tests/unit/domain/ -v --tb=short"),
    ("Code Metrics - File Size Limits", "uv run python -m pytest tests/architecture/test_code_metrics.py::TestFileSizeLimits -v --tb=short"),
    ("Quality Burndown Priorities", "uv run python -m pytest tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries -v --tb=short"),
    ("Quality Debt Scorecard & Exemptions Registry", "uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py -v --tb=short"),
]

# Write header
with open(output_file, "w") as f:
    f.write("=" * 80 + "\n")
    f.write("PYTEST OUTPUT SUMMARY - Exemptions Refactoring Test Suite\n")
    f.write("=" * 80 + "\n\n")

# Run tests
for name, cmd in tests:
    print(f"Running: {name}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    with open(output_file, "a") as f:
        f.write(f"\n{'='*70}\nTEST: {name}\n{'='*70}\n")
        f.write(result.stdout)
        if result.stderr:
            f.write("\nSTDERR:\n" + result.stderr)
        f.write(f"\nReturn code: {result.returncode}\n")

print(f"Output saved to: {output_file}")

# Read and display summary
with open(output_file, "r") as f:
    lines = f.readlines()

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
for line in lines:
    if any(x in line for x in ["passed", "failed", "error", "skipped"]) and "==" in line:
        print(line.rstrip())
