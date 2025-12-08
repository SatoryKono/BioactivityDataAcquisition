from pathlib import Path
import sys
from unittest.mock import patch

import pandas as pd

from bioetl.infrastructure.clients.chembl.impl import (
    ChemblExtractionServiceImpl,
)
from bioetl.infrastructure.observability.factories import default_logging_port
from bioetl.interfaces.cli.app import app

# Force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)
# Create output dir
Path("data/output/assay").mkdir(parents=True, exist_ok=True)

LOGGER = default_logging_port().apply_bind(tool="debug_assay_fetch_v2")


def debug_fetch():
    LOGGER.info("Inspecting input file")
    try:
        df = pd.read_csv("data/input/assay.csv", nrows=10)
        LOGGER.info("Loaded assay IDs", ids=df["assay_chembl_id"].tolist())

        LOGGER.info("Testing single ID fetch")
        test_id = df["assay_chembl_id"].iloc[0]

        from bioetl.domain.configs import ChemblSourceConfig
        from bioetl.infrastructure.clients.chembl.factories import (
            default_chembl_extraction_service,
        )

        config = ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
        )
        service = default_chembl_extraction_service(config)

        LOGGER.info("Requesting batch", test_id=test_id)
        response = service.request_batch(
            "assay",
            [test_id],
            "assay_chembl_id__in",
        )
        LOGGER.info("Response received", keys=list(response.keys()))
        parsed = service.parse_response(response)
        LOGGER.info("Parsed records", count=len(parsed))
        if parsed:
            LOGGER.debug("First record keys", keys=list(parsed[0].keys()))
    except Exception as e:
        LOGGER.error("Fetch error", error=str(e))


if __name__ == "__main__":
    debug_fetch()
    LOGGER.info("Running pipeline")
    sys.argv = [
        "bioetl",
        "run",
        "assay_chembl",
        "--limit",
        "10",
        "--output",
        "data/output/assay",
    ]
    with patch.object(
        ChemblExtractionServiceImpl,
        "get_release_version",
        return_value="chembl_test_v1",
    ):
        try:
            app()
        except SystemExit as e:
            LOGGER.error("Pipeline exited", error=str(e))
        except Exception as e:
            LOGGER.error("Pipeline error", error=str(e))
