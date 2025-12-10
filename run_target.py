#!/usr/bin/env python
"""Wrapper script to run target_chembl pipeline."""

from pathlib import Path
import sys


def main() -> None:
    """Configure path, set arguments, and run the CLI app."""
    src_dir = Path(__file__).parent / "src"
    src_str = str(src_dir)
    if src_str in sys.path:
        sys.path.remove(src_str)
    sys.path.insert(0, src_str)

    from bioetl.interfaces.cli.app import app

    sys.argv = [
        "bioetl",
        "run",
        "target_chembl",
        "--config",
        "configs/pipelines/chembl/target.yaml",
        "--output",
        "data/output/chembl/target",
        "--limit",
        "10",
    ]
    app()


if __name__ == "__main__":
    main()
