import subprocess
import sys

# Run the batch file
result = subprocess.run(
    [r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2\run_all_tests.bat"],
    cwd=r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2"
)
sys.exit(result.returncode)
