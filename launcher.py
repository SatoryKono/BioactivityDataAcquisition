#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run([sys.executable, "test_runner_simple.py"], 
                       cwd=r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2")
sys.exit(result.returncode)
