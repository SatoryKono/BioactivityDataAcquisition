#!/usr/bin/env python3
import subprocess
import sys
import os

os.chdir(r'E:\g-drive\05_AI\github\BioactivityDataAcquisition2')

# Execute the quick test
print("Executing quick test...")
exec(open('quick_test.py').read())

# Generate report
print("\nGenerating report from logs...")
exec(open('generate_report_from_logs.py').read())

print("\nDone!")
