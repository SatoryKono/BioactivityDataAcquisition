import sys
import os
import pandas as pd
from pathlib import Path
from unittest.mock import patch

# Force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)

# Add src to path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

from bioetl.interfaces.cli.app import app
from bioetl.infrastructure.clients.chembl.impl import ChemblExtractionServiceImpl

# Create output dir
Path("data/output/assay").mkdir(parents=True, exist_ok=True)

def debug_fetch():
    print("DEBUG: Inspecting input file...", flush=True)
    try:
        df = pd.read_csv("data/input/assay.csv", nrows=10)
        print(f"First 10 IDs: {df['assay_chembl_id'].tolist()}", flush=True)
        
        print("\nDEBUG: Testing single ID fetch...", flush=True)
        test_id = df['assay_chembl_id'].iloc[0]
        
        from bioetl.infrastructure.config.models import ChemblSourceConfig
        from bioetl.infrastructure.clients.chembl.factories import default_chembl_extraction_service
        
        config = ChemblSourceConfig(base_url="https://www.ebi.ac.uk/chembl/api/data")
        service = default_chembl_extraction_service(config)
        
        print(f"Requesting batch for ID: {test_id}", flush=True)
        response = service.request_batch("assay", [test_id], "assay_chembl_id__in")
        print(f"Response keys: {list(response.keys())}", flush=True)
        parsed = service.parse_response(response)
        print(f"Parsed records: {len(parsed)}", flush=True)
        if parsed:
            print(f"First record keys: {list(parsed[0].keys())}", flush=True)
    except Exception as e:
        print(f"Fetch error: {e}", flush=True)

if __name__ == "__main__":
    debug_fetch()
    print("\n--- Running Pipeline ---", flush=True)
    sys.argv = [
        "bioetl", "run", "assay_chembl",
        "--limit", "10",
        "--output", "data/output/assay"
    ]
    with patch.object(ChemblExtractionServiceImpl, 'get_release_version', return_value="chembl_test_v1"):
        try:
            app()
        except SystemExit as e:
            print(f"SystemExit: {e}", flush=True)
        except Exception as e:
            print(f"Error: {e}", flush=True)

