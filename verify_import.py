import os
import sys

src_path = os.path.abspath(os.path.join(os.getcwd(), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    import bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl as m

    print(f"Module imported: {m}")
    print(f"Attributes: {dir(m)}")
    print(
        f"ChemblExtractionServiceImpl in dir: {'ChemblExtractionServiceImpl' in dir(m)}"
    )
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Exception: {e}")
