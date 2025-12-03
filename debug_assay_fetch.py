import sys
import os
import pandas as pd
from pathlib import Path
from unittest.mock import patch

# Add src to path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

from bioetl.interfaces.cli.app import app
from bioetl.application.services.chembl_extraction import ChemblExtractionService

# Create output dir
Path("data/output/assay").mkdir(parents=True, exist_ok=True)

def debug_fetch():
    print("DEBUG: Inspecting input file...")
    df = pd.read_csv("data/input/assay.csv", nrows=10)
    print(f"First 10 IDs: {df['assay_chembl_id'].tolist()}")
    
    print("\nDEBUG: Testing single ID fetch...")
    # Use a known ID or one from the file
    test_id = df['assay_chembl_id'].iloc[0]
    
    # Simulate what pipeline does
    from bioetl.infrastructure.config.models import ChemblSourceConfig
    from bioetl.infrastructure.clients.chembl.factories import default_chembl_extraction_service
    
    config = ChemblSourceConfig(base_url="https://www.ebi.ac.uk/chembl/api/data")
    service = default_chembl_extraction_service(config)
    
    try:
        print(f"Requesting batch for ID: {test_id}")
        # Note: filter_key should match what pipeline uses: assay_chembl_id__in
        response = service.request_batch("assay", [test_id], "assay_chembl_id__in")
        print(f"Response keys: {list(response.keys())}")
        parsed = service.parse_response(response)
        print(f"Parsed records: {len(parsed)}")
        if parsed:
            print(f"First record keys: {list(parsed[0].keys())}")
    except Exception as e:
        print(f"Fetch error: {e}")

if __name__ == "__main__":
    # Run debug check first
    debug_fetch()

    print("\n--- Running Pipeline ---")
    sys.argv = [
        "bioetl", "run", "assay_chembl",
        "--limit", "10",
        "--output", "data/output/assay"
    ]
    
    with patch.object(ChemblExtractionService, 'get_release_version', return_value="chembl_test_v1"):
        try:
            app()
        except SystemExit as e:
            print(f"SystemExit: {e}")
        except Exception as e:
            print(f"Error: {e}")

