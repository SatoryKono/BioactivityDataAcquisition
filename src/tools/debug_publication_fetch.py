import requests

from bioetl.infrastructure.observability.factories import create_logging_port


def main():
    logger = create_logging_port().apply_bind(
        pipeline="publication_chembl", entity="publication", stage="debug_fetch"
    )

    url = "https://www.ebi.ac.uk/chembl/api/data/document.json?limit=1"
    logger.info("Fetching publication endpoint", url=url)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        logger.info("Fetch succeeded", status_code=resp.status_code)
    except Exception as e:
        logger.error("Fetch failed", error=str(e))


if __name__ == "__main__":
    main()
