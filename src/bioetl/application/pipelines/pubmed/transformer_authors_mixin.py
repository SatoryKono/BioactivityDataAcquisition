"""Author/affiliation helper methods for PubMed transformer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.application.pipelines.pubmed.extractors import (
        RawAuthor,
        StructuredAffiliation,
    )
    from bioetl.domain.ports import PiiHasherPort


class _PubMedTransformerHost(Protocol):
    """Structural host contract for author hashing support."""

    _pii_hasher: PiiHasherPort


class _PubMedTransformerAuthorsMixin:
    """Mixin with PubMed-specific author and affiliation helpers."""

    def _process_structured_affiliations(
        self: _PubMedTransformerHost, affiliations: list[StructuredAffiliation]
    ) -> list[JsonDict]:  # Any: untyped PubMed XML/JSON values
        """Process structured affiliations with PII handling for emails."""
        processed = []
        for aff in affiliations:
            processed_aff: JsonDict = {  # Any: untyped PubMed XML/JSON values
                "text": aff.get("text"),
                "identifier": aff.get("identifier"),
                "identifier_source": aff.get("identifier_source"),
                "ror_id": aff.get("ror_id"),
                "grid_id": aff.get("grid_id"),
            }
            email = aff.get("email")
            if email and self._pii_hasher:
                processed_aff["email_hash"] = self._pii_hasher.hash_value(email)
            else:
                processed_aff["email_hash"] = None

            processed.append(processed_aff)
        return processed

    def _build_authors_with_affiliations(
        self: _PubMedTransformerHost, raw_authors: list[RawAuthor]
    ) -> list[JsonDict]:  # Any: untyped PubMed XML/JSON values
        """Build structured author-affiliation mapping."""
        result: list[JsonDict] = []  # Any: untyped PubMed XML/JSON values

        for author in raw_authors:
            last_name = author.get("last_name")
            initials = author.get("initials")
            fore_name = author.get("fore_name")
            collective = author.get("collective_name")

            if last_name:
                if initials:
                    name = f"{last_name}, {initials}"
                elif fore_name:
                    name = f"{last_name}, {fore_name}"
                else:
                    name = last_name
            elif collective:
                name = collective
            else:
                continue

            name_hash = self._pii_hasher.hash_value(name) if self._pii_hasher else None

            affiliations: list[
                JsonDict  # Any: transformer record has heterogeneous values
            ] = []  # Any: untyped PubMed XML/JSON values
            structured_affs = author.get("structured_affiliations") or []

            for aff in structured_affs:
                aff_entry: JsonDict = {  # Any: untyped PubMed XML/JSON values
                    "text": aff.get("text"),
                    "ror_id": aff.get("ror_id"),
                    "grid_id": aff.get("grid_id"),
                    "identifier": aff.get("identifier"),
                    "identifier_source": aff.get("identifier_source"),
                }
                affiliations.append(aff_entry)

            result.append(
                {
                    "name_hash": name_hash,
                    "initials": initials,
                    "affiliations": affiliations,
                }
            )

        return result


__all__ = ["_PubMedTransformerAuthorsMixin"]
