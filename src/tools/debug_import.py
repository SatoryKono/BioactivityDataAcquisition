import os
import sys

print(f"CWD: {os.getcwd()}")
if "src" not in sys.path:
    sys.path.insert(0, os.path.join(os.getcwd(), "src"))

try:
    print("Import successful")
except Exception as e:
    print(f"Import failed: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()

try:
    print("Class import successful")
except Exception as e:
    print(f"Class import failed: {e}")

