from pathlib import Path
import sys
from unittest.mock import patch

from bioetl.infrastructure.observability.factories import create_logging_port

# Ensure output dir exists
Path("data/output/target").mkdir(parents=True, exist_ok=True)

logger = create_logging_port().apply_bind(tool="run_cmd")

try:
    # print(f"Container module: {bioetl.application.container.__file__}")
    from bioetl.infrastructure.clients.chembl.impl import ChemblExtractionServiceImpl
    from bioetl.interfaces.cli.app import app
except ImportError as e:
    logger.error("Failed to import CLI dependencies", error=str(e))
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

    logger.info("Running CLI app via wrapper")

    # Patch get_release_version to avoid /status call
    with patch.object(
        ChemblExtractionServiceImpl,
        "get_release_version",
        return_value="chembl_mock",
    ):
        try:
            app()
        except SystemExit as e:
            logger.error("CLI exited", error=str(e))
        except Exception as e:
            logger.error("Wrapper error", error=str(e))
        finally:
            logger.info("Wrapper finished")


if __name__ == "__main__":
    main()
