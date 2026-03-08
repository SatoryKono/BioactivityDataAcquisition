#!/usr/bin/env python
"""Execute exemptions refactoring pytest suite with consolidated output."""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import re

def run_command(cmd, description):
    """Run a command and capture output."""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(Path.cwd())
        )
        
        output = result.stdout
        if result.stderr:
            output += "\nSTDERR:\n" + result.stderr
        
        print(output[:1000] + ("..." if len(output) > 1000 else ""))  # Print first 1000 chars
        
        return output, result.returncode
    except Exception as e:
        print(f"ERROR: {e}")
        return str(e), 1

def parse_pytest_summary(text):
    """Extract test statistics from pytest output."""
    stats = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'error': 0,
        'duration': ''
    }
    
    # Look for pytest summary line
    for line in text.split('\n'):
        if 'passed' in line or 'failed' in line or 'error' in line:
            if '==' in line:
                # Extract numbers
                passed_match = re.search(r'(\d+)\s+passed', line)
                failed_match = re.search(r'(\d+)\s+failed', line)
                error_match = re.search(r'(\d+)\s+error', line)
                skipped_match = re.search(r'(\d+)\s+skipped', line)
                duration_match = re.search(r'([\d.]+)s', line)
                
                if passed_match:
                    stats['passed'] += int(passed_match.group(1))
                if failed_match:
                    stats['failed'] += int(failed_match.group(1))
                if error_match:
                    stats['error'] += int(error_match.group(1))
                if skipped_match:
                    stats['skipped'] += int(skipped_match.group(1))
                if duration_match:
                    stats['duration'] = duration_match.group(1)
    
    return stats

def main():
    """Main execution function."""
    
    # Setup output directory
    output_dir = Path("reports/exemptions_refactoring")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "pytest-output.txt"
    
    print(f"\nPytest Exemptions Refactoring Test Suite")
    print(f"Output file: {output_file}")
    print(f"Working directory: {Path.cwd()}\n")
    
    # Initialize output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("PYTEST OUTPUT SUMMARY - Exemptions Refactoring Test Suite\n")
        f.write("=" * 80 + "\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Working directory: {Path.cwd()}\n\n")
    
    # Define tests
    tests = [
        (
            "Unit Domain Tests",
            'uv run python -m pytest tests/unit/domain/ -v --tb=short'
        ),
        (
            "Code Metrics - File Size Limits",
            'uv run python -m pytest tests/architecture/test_code_metrics.py::TestFileSizeLimits -v --tb=short'
        ),
        (
            "Quality Burndown Priorities",
            'uv run python -m pytest tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries -v --tb=short'
        ),
        (
            "Quality Debt Scorecard & Exemptions Registry",
            'uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py -v --tb=short'
        ),
    ]
    
    all_stats = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'error': 0,
    }
    
    results = []
    
    # Run all tests
    for test_name, cmd in tests:
        output, return_code = run_command(cmd, test_name)
        
        # Parse statistics
        stats = parse_pytest_summary(output)
        all_stats['passed'] += stats['passed']
        all_stats['failed'] += stats['failed']
        all_stats['skipped'] += stats['skipped']
        all_stats['error'] += stats['error']
        
        results.append({
            'name': test_name,
            'cmd': cmd,
            'output': output,
            'return_code': return_code,
            'stats': stats
        })
        
        # Append to file
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"TEST: {test_name}\n")
            f.write(f"{'='*70}\n")
            f.write(f"Command: {cmd}\n\n")
            f.write(output)
            f.write(f"\n\nReturn code: {return_code}\n")
    
    # Write summary to file
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"\n\n{'='*70}\n")
        f.write("AGGREGATE TEST SUMMARY\n")
        f.write(f"{'='*70}\n\n")
        
        total = all_stats['passed'] + all_stats['failed'] + all_stats['error'] + all_stats['skipped']
        f.write(f"Total tests run: {total}\n")
        f.write(f"Passed: {all_stats['passed']}\n")
        f.write(f"Failed: {all_stats['failed']}\n")
        f.write(f"Errors: {all_stats['error']}\n")
        f.write(f"Skipped: {all_stats['skipped']}\n\n")
        
        f.write("Individual Test Results:\n")
        for result in results:
            f.write(f"\n  {result['name']}:\n")
            f.write(f"    Passed: {result['stats']['passed']}\n")
            f.write(f"    Failed: {result['stats']['failed']}\n")
            f.write(f"    Skipped: {result['stats']['skipped']}\n")
            f.write(f"    Errors: {result['stats']['error']}\n")
            f.write(f"    Return code: {result['return_code']}\n")
    
    # Print final summary
    print(f"\n{'='*70}")
    print("FINAL TEST SUMMARY")
    print(f"{'='*70}\n")
    
    total = all_stats['passed'] + all_stats['failed'] + all_stats['error'] + all_stats['skipped']
    print(f"Total tests run: {total}")
    print(f"✓ Passed: {all_stats['passed']}")
    if all_stats['failed'] > 0:
        print(f"✗ Failed: {all_stats['failed']}")
    if all_stats['error'] > 0:
        print(f"⚠ Errors: {all_stats['error']}")
    if all_stats['skipped'] > 0:
        print(f"⊘ Skipped: {all_stats['skipped']}")
    
    print(f"\nIndividual Results:")
    for result in results:
        print(f"  • {result['name']}: {result['stats']['passed']} passed, "
              f"{result['stats']['failed']} failed, {result['stats']['error']} error")
    
    print(f"\nFull output saved to: {output_file}")
    
    return 0 if all_stats['failed'] == 0 and all_stats['error'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
