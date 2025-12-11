#!/usr/bin/env python
"""Unified wrapper script to run ChEMBL pipelines.

Usage:
    python run_pipeline.py activity    # Run activity_chembl pipeline
    python run_pipeline.py assay       # Run assay_chembl pipeline
    python run_pipeline.py molecule    # Run molecule_chembl pipeline
    python run_pipeline.py target      # Run target_chembl pipeline
    python run_pipeline.py publication # Run publication_chembl pipeline

This script replaces the individual run_*.py scripts for a cleaner interface.
"""

from pathlib import Path
import sys

PIPELINES = {
    "activity": {
        "name": "activity_chembl",
        "config": "configs/pipelines/chembl/activity.yaml",
        "output": "data/output/chembl/activity",
    },
    "assay": {
        "name": "assay_chembl",
        "config": "configs/pipelines/chembl/assay.yaml",
        "output": "data/output/chembl/assay",
    },
    "molecule": {
        "name": "molecule_chembl",
        "config": "configs/pipelines/chembl/molecule.yaml",
        "output": "data/output/chembl/molecule",
    },
    "target": {
        "name": "target_chembl",
        "config": "configs/pipelines/chembl/target.yaml",
        "output": "data/output/chembl/target",
    },
    "publication": {
        "name": "publication_chembl",
        "config": "configs/pipelines/chembl/publication.yaml",
        "output": "data/output/chembl/publication",
    },
}


def main() -> None:
    """Configure path, set arguments, and run the CLI app."""
    if len(sys.argv) < 2 or sys.argv[1] not in PIPELINES:
        print(f"Usage: {sys.argv[0]} <pipeline>")
        print(f"Available pipelines: {', '.join(PIPELINES.keys())}")
        sys.exit(1)

    pipeline_key = sys.argv[1]
    pipeline = PIPELINES[pipeline_key]

    # Configure path
    src_dir = Path(__file__).parent / "src"
    src_str = str(src_dir)
    if src_str in sys.path:
        sys.path.remove(src_str)
    sys.path.insert(0, src_str)

    from bioetl.interfaces.cli.app import app

    # Set CLI arguments
    # Pass through additional CLI arguments (e.g., --limit, --dry-run)
    base_args = [
        "bioetl",
        "run",
        pipeline["name"],
        "--config",
        pipeline["config"],
        "--output",
        pipeline["output"],
    ]
    # Append any additional arguments passed to this script
    sys.argv = base_args + sys.argv[2:]
    app()


if __name__ == "__main__":
    main()
