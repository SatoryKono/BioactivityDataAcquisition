import sys
import os
print(f"CWD: {os.getcwd()}")
# Ensure src is in path
if "src" not in sys.path:
    sys.path.insert(0, os.path.join(os.getcwd(), "src"))

try:
    import bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl
    print("Import successful")
except Exception as e:
    print(f"Import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Also try importing the class
try:
    from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import ChemblExtractionServiceImpl
    print("Class import successful")
except Exception as e:
    print(f"Class import failed: {e}")
