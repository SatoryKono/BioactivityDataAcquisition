import os
import sys
from pathlib import Path

import pandas as pd

# Add src to python path
sys.path.append(os.path.abspath("src"))

print("Script started")

try:
    from bioetl.domain.schemas.chembl.activity import ActivitySchema
    print("Schema imported")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

def main():
    path = Path("qc/golden/chembl_activity/expected_output.csv")
    if not path.exists():
        print(f"File not found: {path}")
        # Try absolute path just in case
        path = Path(os.getcwd()) / "qc/golden/chembl_activity/expected_output.csv"
        if not path.exists():
            print(f"File still not found at {path}")
            return

    print(f"Reading {path}")
    df = pd.read_csv(path)
    
    # Get columns from schema to ensure correct order
    schema = ActivitySchema.to_schema()
    expected_columns = list(schema.columns.keys())
    
    print("Reordering columns...")
    missing = [c for c in expected_columns if c not in df.columns]
    if missing:
        print(f"Error: Missing columns in CSV: {missing}")
        return

    df = df[expected_columns]
    
    print(f"Writing back to {path}")
    df.to_csv(path, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
