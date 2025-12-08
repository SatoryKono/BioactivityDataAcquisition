import time

import requests

from bioetl.infrastructure.observability.factories import default_logging_port


LOGGER = default_logging_port().apply_bind(tool="check_net")


def check(url):
    LOGGER.info("Fetching URL", url=url)
    try:
        start = time.time()
        resp = requests.get(url, timeout=10)
        LOGGER.info(
            "Received response", status=resp.status_code, duration_sec=time.time() - start
        )
        LOGGER.debug("Response preview", body=resp.text[:200])
    except Exception as e:  # pragma: no cover - diagnostic helper
        LOGGER.error("Network check failed", error=str(e))


# check("https://www.ebi.ac.uk/chembl/api/data/status")
check("https://www.ebi.ac.uk/chembl/api/data/molecule?limit=1")
