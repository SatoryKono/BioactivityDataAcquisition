"""Application-owned normalization rule sets for Bronze -> Silver processing."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["NormalizationRulesPolicy"]


@dataclass(frozen=True, slots=True)
class NormalizationRulesPolicy:
    """Deterministic field buckets for centralized record normalization."""

    doi_fields: frozenset[str] = field(
        default_factory=lambda: frozenset({"doi", "publication_doi"})
    )
    pmid_fields: frozenset[str] = field(
        default_factory=lambda: frozenset({"pmid", "publication_pmid"})
    )
    date_fields: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "publication_date",
                "published",
                "published_online",
                "published_print",
                "deposition_date",
                "created_date",
                "updated_date",
            }
        )
    )
    title_fields: frozenset[str] = field(default_factory=lambda: frozenset({"title"}))
    abstract_fields: frozenset[str] = field(
        default_factory=lambda: frozenset({"abstract"})
    )
    oa_status_fields: frozenset[str] = field(
        default_factory=lambda: frozenset({"oa_status", "open_access_status"})
    )
    passthrough_fields: frozenset[str] = field(
        default_factory=lambda: frozenset({"entity_id", "content_hash"})
    )
