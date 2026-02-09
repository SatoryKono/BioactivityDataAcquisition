from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
import pandas as pd
schema = PubMedPublicationSchema.to_schema()
print(f"Checks for pmid: {schema.columns['pmid'].checks}")
