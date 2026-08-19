"""Facade exports for OpenAlex field extraction functions."""

from __future__ import annotations

from bioetl.application.pipelines.openalex._extractors_authors import *  # noqa: F403
from bioetl.application.pipelines.openalex._extractors_authors import (
    __all__ as _AUTHOR_EXPORTS,
)
from bioetl.application.pipelines.openalex._extractors_publication_fields import *  # noqa: F403
from bioetl.application.pipelines.openalex._extractors_publication_fields import (
    __all__ as _PUBLICATION_FIELD_EXPORTS,
)
from bioetl.application.pipelines.openalex._extractors_topics_grants import *  # noqa: F403
from bioetl.application.pipelines.openalex._extractors_topics_grants import (
    __all__ as _TOPIC_GRANT_EXPORTS,
)

__all__ = [*_AUTHOR_EXPORTS, *_PUBLICATION_FIELD_EXPORTS, *_TOPIC_GRANT_EXPORTS]
