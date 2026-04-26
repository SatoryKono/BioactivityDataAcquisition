import httpx
import pandas as pd

from bioetl.domain.normalization.profiles.chembl_publication import (
    CHEMBL_PUBLICATION_PROFILE,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema

response = httpx.get(
    "https://www.ebi.ac.uk/chembl/api/data/document?format=json&limit=1&offset=0&doc_type=PUBLICATION&year__gte=1950&year__lte=2050"
)
doc = response.json()["documents"][0]

# mock meta fields
for f in [
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_ingestion_ts",
    "_index",
    "_lookup_method",
    "_original_id",
    "_source",
    "_dq_error",
    "_dq_warn",
]:
    doc[f] = "test"
doc["_ingestion_ts"] = pd.Timestamp("2024-01-01T00:00:00Z")

df = pd.DataFrame([doc])
normalized_df = CHEMBL_PUBLICATION_PROFILE.normalize(df)

try:
    ChemblPublicationSchema.validate(normalized_df)
    print("Success")
except Exception as e:
    if hasattr(e, "failure_cases"):
        print(e.failure_cases)
    else:
        print(e)
