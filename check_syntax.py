import ast
import sys
import traceback

files = [
    r"E:/google_drive/05_AI/github/BioactivityDataAcquisition2/tests/e2e/conftest.py",
    r"E:/google_drive/05_AI/github/BioactivityDataAcquisition2/tests/e2e/test_full_pipeline.py",
    r"E:/google_drive/05_AI/github/BioactivityDataAcquisition2/tests/infrastructure/adapters/test_uniprot.py",
    r"E:/google_drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/core/executor.py",
]

for file_path in files:
    print(f"Checking {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
        print("OK")
    except Exception:
        print(f"Error in {file_path}:")
        traceback.print_exc()
