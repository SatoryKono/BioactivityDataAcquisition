import os
import subprocess
os.chdir(r'E:\g-drive\05_AI\github\BioactivityDataAcquisition2')
result = subprocess.run([r'E:\g-drive\05_AI\github\BioactivityDataAcquisition2\.venv\Scripts\python.exe', r'E:\g-drive\05_AI\github\BioactivityDataAcquisition2\comprehensive_test_runner.py'], shell=True)
print(f"Process exited with code: {result.returncode}")
