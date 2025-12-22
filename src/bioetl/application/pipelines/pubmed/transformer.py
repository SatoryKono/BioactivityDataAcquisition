"""PubMed Publication Transformer."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Publication
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


def _parse_author_list(article_node: ET.Element) -> list[str]:
    """Извлекает список авторов из XML-узла статьи."""
    author_list_node = article_node.find(".//AuthorList")
    if author_list_node is None:
        return []

    authors = []
    for author_node in author_list_node.findall(".//Author"):
        last_name_node = author_node.find("LastName")
        initials_node = author_node.find("Initials")
        if last_name_node is not None and initials_node is not None:
            authors.append(f"{last_name_node.text}, {initials_node.text}")
    return authors


def _get_node_text(node: ET.Element | None) -> str | None:
    """Extract text from an XML node, returning None if node is None."""
    return node.text if node is not None else None


def _get_publication_year(node: ET.Element | None) -> int | None:
    """Extract publication year from a node, returning None if invalid."""
    if node is not None and node.text:
        return int(node.text)
    return None


def _extract_business_data(article_node: ET.Element, pmid: str) -> dict:
    """Extract business data from article XML node."""
    return {
        "pmid": pmid,
        "title": _get_node_text(article_node.find(".//ArticleTitle")),
        "abstract": _get_node_text(article_node.find(".//Abstract/AbstractText")),
        "journal": _get_node_text(article_node.find(".//Journal/Title")),
        "publication_year": _get_publication_year(article_node.find(".//PubDate/Year")),
        "authors": _parse_author_list(article_node),
    }


class PubMedPublicationTransformer(BaseTransformer):
    """Transformer for PubMed publication records."""

    def __init__(self, provider: str = "pubmed"):
        super().__init__(provider)

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Трансформирует сырую XML-запись в формат Silver."""
        raw_xml = record.get("_raw_xml")
        if not raw_xml or not isinstance(raw_xml, str):
            return None

        try:
            article_node = ET.fromstring(raw_xml)
            pmid = _get_node_text(article_node.find(".//PMID"))
            if not pmid:
                return None

            business_data = _extract_business_data(article_node, pmid)
            entity_id = generate_entity_id(
                record={"pmid": pmid},
                provider=self.provider,
                id_field="pmid",
            )
            content_hash = self.compute_content_hash(business_data, exclude_none=False)

            publication = Publication(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id=None,
                **business_data,
            )
            return cast("SilverRecord", self.entity_to_silver_record(publication))

        except ET.ParseError as e:
            context.logger.warning(
                "XML_parse_error", error=str(e), pmid=record.get("pmid")
            )
            return None
