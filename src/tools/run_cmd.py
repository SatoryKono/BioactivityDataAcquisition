import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

# Ensure output dir exists
Path("data/output/target").mkdir(parents=True, exist_ok=True)

try:
    from bioetl.infrastructure.services.chembl_extraction import (
        ChemblExtractionServiceImpl,
    )

    import bioetl.application.container

    # print(f"Container module: {bioetl.application.container.__file__}")
    from bioetl.interfaces.cli.app import app
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)


def main():
    # Simulate CLI arguments
    # python -m bioetl run target_chembl --config ... --output ... --limit 10
    sys.argv = [
        "bioetl",
        "run",
        "target_chembl",
        "--config",
        "configs/pipelines/chembl/target.yaml",
        "--output",
        "data/output/target",
        "--limit",
        "10",
    ]

    print("Running CLI app via wrapper...")

    # Patch get_release_version to avoid /status call
    with patch.object(
        ChemblExtractionServiceImpl, "get_release_version", return_value="chembl_mock"
    ):
        try:
            app()
        except SystemExit as e:
            print(f"SystemExit: {e}")
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            print("Wrapper finished.")


if __name__ == "__main__":
    main()
