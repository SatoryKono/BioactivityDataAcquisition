import sys
import os
from pathlib import Path

# Add src to path
src_path = os.path.abspath("src")
print(f"Adding to path: {src_path}")
sys.path.insert(0, src_path)

print(f"sys.path: {sys.path}")

try:
    import bioetl
    print(f"bioetl found at: {bioetl.__file__}")
except ImportError as e:
    print(f"ImportError: {e}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

# Create output dir
output_dir = Path("data/output/document")
output_dir.mkdir(parents=True, exist_ok=True)

# Import and run app
from bioetl.interfaces.cli.app import app

# Simulate arguments
sys.argv = [
    "bioetl", "run", "document_chembl",
    "--config", "configs/pipelines/chembl/document.yaml",
    "--output", "data/output/document",
    "--limit", "10"
]

# Run
if __name__ == "__main__":
    app()

