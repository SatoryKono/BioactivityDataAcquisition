import os
from pathlib import Path
import sys

import pandas as pd

# Add src to python path
sys.path.append(os.path.abspath("src"))

from bioetl.infrastructure.observability.factories import create_logging_port

LOGGER = create_logging_port().apply_bind(tool="update_golden_columns")

LOGGER.info("Script started")

try:
    from bioetl.domain.schemas.chembl.activity import ActivityTableSchema

    LOGGER.info("Schema imported")
except ImportError as e:
    LOGGER.error("Failed to import schema", error=str(e))
    sys.exit(1)


def main():
    path = Path("qc/golden/chembl_activity/expected_output.csv")
    if not path.exists():
        LOGGER.error("Golden file not found", path=str(path))
        # Try absolute path just in case
        path = Path(os.getcwd()) / "qc/golden/chembl_activity/expected_output.csv"
        if not path.exists():
            LOGGER.error("Golden file still missing after fallback", path=str(path))
            return

    LOGGER.info("Reading golden file", path=str(path))
    df = pd.read_csv(path)

    # Get columns from schema to ensure correct order
    schema = ActivityTableSchema.to_schema()
    expected_columns = list(schema.columns.keys())

    LOGGER.info("Reordering columns to match schema")
    missing = [c for c in expected_columns if c not in df.columns]
    if missing:
        LOGGER.error("Missing columns in CSV", missing_columns=missing)
        return

    df = df[expected_columns]

    LOGGER.info("Writing reordered CSV", path=str(path))
    df.to_csv(path, index=False)
    LOGGER.info("Column update completed")


if __name__ == "__main__":
    main()
