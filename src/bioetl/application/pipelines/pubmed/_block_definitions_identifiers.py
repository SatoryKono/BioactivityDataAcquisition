"""Identifier and core record blocks for PubMed publication pipeline."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubmed._block_definitions_base import _PubMedXmlBlock
from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)
from bioetl.application.pipelines.pubmed.xml_parser import get_text
from bioetl.domain.normalization import normalize_pmc_id
from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.domain.value_objects.publications import DOI, PubMedId

if TYPE_CHECKING:
    from bioetl.domain.ports import DataNormalizationPort


class _PubMedIdentifierBlock(_PubMedXmlBlock):
    """Extract PubMed identifiers from cached XML root."""

    def __init__(
        self,
        *,
        data_normalizer: DataNormalizationPort,
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._data_normalizer = data_normalizer

    def extract(self, record: BronzeRecord) -> JsonDict:
        del record
        root = self._resolve_root()
        if root is None:
            return {"pmid": None}

        identifiers = IdentifierExtractor.extract_all_identifiers(root)
        raw_pmid = get_text(root.find(".//PMID"))
        pmid_vo = PubMedId.from_raw(raw_pmid)
        if root.find(".//Article") is None:
            return {"pmid": str(pmid_vo) if pmid_vo else None}

        doi_vo = DOI.from_raw(identifiers["doi"])
        return {
            "pmid": str(pmid_vo) if pmid_vo else None,
            "doi": str(doi_vo) if doi_vo else None,
            "pii": self._data_normalizer.normalize_to_string(identifiers["pii"]),
            "mid": self._data_normalizer.normalize_to_string(identifiers["mid"]),
            "publisher_id": self._data_normalizer.normalize_to_string(
                identifiers["publisher_id"]
            ),
            "pmc_id": normalize_pmc_id(identifiers["pmc_id"]),
        }


class _PubMedCoreBlock(_PubMedXmlBlock):
    """Extract core publication content and lineage metadata."""

    def __init__(
        self,
        *,
        data_normalizer: DataNormalizationPort,
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._data_normalizer = data_normalizer

    def extract(self, record: BronzeRecord) -> JsonDict:
        article, _, _ = self._resolve_article_context()
        if article is None:
            return {}

        return {
            "title": get_text(article.find(".//ArticleTitle")),
            "abstract": self._data_normalizer.strip_html_tags(
                AbstractExtractor.extract_abstract(article)
            ),
            "abstract_structured": AbstractExtractor.is_abstract_structured(article),
            "language": get_text(article.find(".//Language")),
            "_source": "pubmed",
            "citations_received": None,
            "is_oa": None,
            "_lookup_method": record.get("_lookup_method", "pmid"),
            "_original_id": record.get("_original_id"),
            "_dq_warn": False,
            "_dq_error": False,
        }


__all__ = ["_PubMedCoreBlock", "_PubMedIdentifierBlock"]
