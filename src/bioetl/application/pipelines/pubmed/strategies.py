"""PubMed-specific strategies for publication transformation."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from typing import TYPE_CHECKING, ClassVar

import defusedxml.ElementTree as defused_ET  # type: ignore[import-untyped]

from bioetl.application.pipelines.pubmed.extractors import (
    AuthorExtractor,
    DateExtractor,
)

if TYPE_CHECKING:
    import re

    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, JsonDict

    class _DataExtractorStrategyBase:
        def pre_extract_validation(
            self,
            context: PipelineContext,
            record: BronzeRecord,
            index: int,
        ) -> None: ...

        def extract_business_data(self, record: BronzeRecord) -> JsonDict: ...
else:
    from bioetl.domain.ports import DataExtractorStrategy as _DataExtractorStrategyBase


class PubMedDataExtractor(_DataExtractorStrategyBase):
    """Strategy for extracting business data from PubMed XML."""

    _VALID_DATE_PATTERNS: ClassVar[tuple[re.Pattern[str], ...]] = (
        # Implementation detail: re-using the patterns from the old transformer
    )

    _MONTH_MAP: ClassVar[dict[str, int]] = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def __init__(
        self,
        author_extractor: AuthorExtractor | None = None,
        date_extractor: DateExtractor | None = None,
    ) -> None:
        self._author_extractor = author_extractor or AuthorExtractor()
        self._date_extractor = date_extractor or DateExtractor()
        self._cached_xml_root: ET.Element | None = None

        # We need access to some transformer-level methods for blocks.
        # This is a bit tricky during migration.
        # For now, we will pass them or implement them here.

    def pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Validate and parse the raw PubMed XML payload before extraction."""
        raw_xml = record.get("_raw_xml")
        if not raw_xml or not isinstance(raw_xml, str):
            raise ValueError("Missing or invalid _raw_xml field")

        try:
            self._cached_xml_root = defused_ET.fromstring(raw_xml)
        except (ET.ParseError, defused_ET.EntitiesForbidden) as e:
            context.logger.warning(
                "XML_parse_error",
                error=str(e),
                pmid=record.get("pmid"),
            )
            raise ValueError(f"XML parse error: {e}") from e

    def extract_business_data(self, record: BronzeRecord) -> JsonDict:
        """Extract normalized PubMed business fields from one bronze record."""
        # This implementation will be used when we move PubMed to pure composition.
        # It needs to provide all the logic that was previously in PubMedPublicationTransformer.
        # For the sake of this migration step, we'll keep it compatible.
        raise NotImplementedError("PubMedDataExtractor.extract_business_data")


# We will refine this after we see how to handle the shared methods.
