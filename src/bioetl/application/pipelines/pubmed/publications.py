# src/bioetl/application/pipelines/pubmed/publications.py
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base import BasePipeline
from bioetl.domain.entities import Publication
from bioetl.domain.transformations import generate_content_hash, generate_entity_id
from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord

# Need SilverRecord available at runtime for cast
if TYPE_CHECKING:
    from bioetl.domain.types import SilverRecord


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


class PubMedPublicationsPipeline(BasePipeline):
    """Пайплайн для данных о публикациях из PubMed."""

    async def transform_bronze_to_silver(
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
                "publication_year": int(pub_year_node.text)
                if pub_year_node is not None and pub_year_node.text
                else None,
                "authors": _parse_author_list(article_node),
            }

            entity_id = generate_entity_id(
                record={"pmid": pmid},
                provider=self.provider,
                id_field="pmid",
            )
            content_hash = generate_content_hash(business_data, self.provider)

            publication = Publication(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id=None,
                **business_data,
            )

            silver_record: dict[str, Any] = {
                "entity_id": publication.entity_id,
                "content_hash": publication.content_hash,
                "pmid": publication.pmid,
                "title": publication.title,
                "abstract": publication.abstract,
                "journal": publication.journal,
                "publication_year": publication.publication_year,
                "authors": publication.authors,
                "_run_id": str(context.run_id),
                "_run_type": str(context.run_type.value),
                "_ingestion_ts": datetime.now(UTC).isoformat(),
            }

            return cast("SilverRecord", silver_record)

        except ET.ParseError as e:
            self.logger.warning(
                "XML_parse_error", error=str(e), pmid=record.get("pmid")
            )
            return None

    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract PMID as watermark."""
        pmid = record.get("pmid", "")
        return Watermark.from_id(str(pmid))
