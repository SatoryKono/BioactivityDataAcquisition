from pathlib import Path

p = Path(r'E:\g-drive\05_AI\github\BioactivityDataAcquisition2\docs\reports\evidence\project-legacy-compatibility-remediation\03-synthesis\CROSS-SYNTHESIS-project-legacy-compatibility-remediation.md')

print(f'Path: {p}')
print(f'Exists: {p.exists()}')

try:
    is_file = p.is_file()
    print(f'Is file: {is_file}')
except OSError as e:
    print(f'OSError caught: {e}')
    print(f'Error number: {e.errno}')
