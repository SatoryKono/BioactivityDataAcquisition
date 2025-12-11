import sys

from bioetl.infrastructure.observability.factories import create_logging_port
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
    logger = create_logging_port().apply_bind(tool="run_pipeline")
    logger.info("Starting pipeline via wrapper script")
    try:
        app()
    except SystemExit as e:
        logger.error("Pipeline exited", error=str(e))
