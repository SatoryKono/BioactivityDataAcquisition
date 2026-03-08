#!/usr/bin/env python3
"""Launch tests from within Python."""
import subprocess
import sys

if __name__ == "__main__":
    result = subprocess.run([sys.executable, "final_test_runner.py"], cwd=r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2")
    sys.exit(result.returncode)
