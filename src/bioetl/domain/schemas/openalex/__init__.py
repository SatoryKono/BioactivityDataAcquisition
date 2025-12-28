"""OpenAlex Pandera schemas for Silver layer validation.

Provides schemas for OpenAlex entities: works, authors, institutions, sources,
and relationship tables (authorship, topics, mesh terms).
"""

from bioetl.domain.schemas.openalex.author import OpenAlexAuthorSchema
from bioetl.domain.schemas.openalex.institution import OpenAlexInstitutionSchema
from bioetl.domain.schemas.openalex.source import OpenAlexSourceSchema
from bioetl.domain.schemas.openalex.work import OpenAlexWorkSchema
from bioetl.domain.schemas.openalex.work_authorship import OpenAlexWorkAuthorshipSchema
from bioetl.domain.schemas.openalex.work_mesh import OpenAlexWorkMeshSchema
from bioetl.domain.schemas.openalex.work_topic import OpenAlexWorkTopicSchema

__all__ = [
    "OpenAlexAuthorSchema",
    "OpenAlexInstitutionSchema",
    "OpenAlexSourceSchema",
    "OpenAlexWorkAuthorshipSchema",
    "OpenAlexWorkMeshSchema",
    "OpenAlexWorkSchema",
    "OpenAlexWorkTopicSchema",
]
