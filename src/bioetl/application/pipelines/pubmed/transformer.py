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
    authors = []
    author_list_node = article_node.find(".//AuthorList")
    if author_list_node is None:
        return []

    for author_node in author_list_node.findall(".//Author"):
        last_name_node = author_node.find("LastName")
        initials_node = author_node.find("Initials")
        if last_name_node is not None and initials_node is not None:
            authors.append(f"{last_name_node.text}, {initials_node.text}")
    return authors


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
            pmid_node = article_node.find(".//PMID")
            pmid = pmid_node.text if pmid_node is not None else None

            if not pmid:
                return None

            title_node = article_node.find(".//ArticleTitle")
            journal_node = article_node.find(".//Journal/Title")
            pub_year_node = article_node.find(".//PubDate/Year")
            abstract_node = article_node.find(".//Abstract/AbstractText")

            business_data = {
                "pmid": pmid,
                "title": title_node.text if title_node is not None else None,
                "abstract": abstract_node.text if abstract_node is not None else None,
                "journal": journal_node.text if journal_node is not None else None,
                "publication_year": (
                    int(pub_year_node.text)
                    if pub_year_node is not None and pub_year_node.text
                    else None
                ),
                "authors": _parse_author_list(article_node),
            }

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

            # Convert Entity to SilverRecord for storage
            silver_record = self.entity_to_silver_record(publication)

            return cast("SilverRecord", silver_record)

        except ET.ParseError as e:
            context.logger.warning(
                "XML_parse_error", error=str(e), pmid=record.get("pmid")
            )
            return None
