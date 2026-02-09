from bioetl.domain.schemas.common.publication_base import PublicationBaseSchema
import pandas as pd
schema = PublicationBaseSchema.to_schema()
print(f"Base checks for pmid: {schema.columns['pmid'].checks}")
