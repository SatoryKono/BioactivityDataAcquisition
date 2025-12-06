import os
import sys
from pathlib import Path

# Import and run app
from bioetl.interfaces.cli.app import app

# Mock sys.argv
sys.argv = [
    "bioetl",
    "run",
    "target_chembl",
    "--config",
    "configs/pipelines/chembl/target.yaml",
    "--output",
    "data/output/target",
    "--limit",
    "100",
]

if __name__ == "__main__":
    print("Starting pipeline via wrapper script...")
    try:
        app()
    except SystemExit as e:
        print(f"SystemExit: {e}")
