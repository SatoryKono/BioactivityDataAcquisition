import argparse
import sys
import logging
from bioetl.infrastructure.monitoring import configure_logging

def main() -> None:
    parser = argparse.ArgumentParser(description="BioETL Pipeline Runner")
    parser.add_argument("--config", type=str, required=True, help="Path to pipeline config")
    parser.add_argument("--dry-run", action="store_true", help="Run without side effects")
    args = parser.parse_args()

    configure_logging(pipeline="unknown", run_id="boot")
    logger = logging.getLogger(__name__)

    logger.info(f"Starting BioETL with config: {args.config}")

    # Placeholder for application logic
    if args.dry_run:
        logger.info("Dry run enabled. No changes will be applied.")

if __name__ == "__main__":
    main()
