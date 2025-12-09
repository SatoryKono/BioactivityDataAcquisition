import sys
import os

# Setup sys.path
src_path = os.path.abspath(os.path.join(os.getcwd(), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

print(f"sys.path: {sys.path}")

print("Importing DataClientABC...")
try:
    from bioetl.domain.clients.contracts import DataClientABC
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Importing LoggingPortABC...")
try:
    from bioetl.domain.observability.contracts import LoggingPortABC
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Importing ExtractionServiceABC...")
try:
    from bioetl.domain.ports.extraction import ExtractionServiceABC
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Importing DefaultFieldProviderABC...")
try:
    from bioetl.domain.ports.providers import DefaultFieldProviderABC
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Importing ChemblPaginatorImpl...")
try:
    from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginatorImpl
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Importing ChemblResponseParserImpl...")
try:
    from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParserImpl
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Importing serialize_chembl_payload...")
try:
    from bioetl.infrastructure.clients.chembl.serializers import serialize_chembl_payload
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Importing default_logging_port...")
try:
    from bioetl.infrastructure.observability.factories import default_logging_port
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")

print("Importing ChemblExtractionServiceImpl...")
try:
    from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import ChemblExtractionServiceImpl
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
