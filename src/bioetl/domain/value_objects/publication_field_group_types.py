"""Publication field-group enums and mapping tables."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from bioetl.domain.value_objects._publication_field_groups_data import (
    FIELD_TO_GROUP_VALUE_MAPPING,
    GROUP_DISPLAY_NAMES_BY_VALUE,
)

__all__ = [
    "FIELD_TO_GROUP_MAPPING",
    "PublicationFieldGroup",
]


class PublicationFieldGroup(StrEnum):
    """Semantic groups for publication fields."""

    ID_AND_STATUS = "id_and_status"
    BIBLIOGRAPHY = "bibliography"
    AUTHOR_AND_AFFILIATIONS = "author_and_affiliations"
    TERMS_AND_KEYWORDS_AND_TOPICS = "terms_and_keywords_and_topics"
    CITATIONS_AND_REFERENCE = "citations_and_reference"
    DATE_AND_PLACES = "date_and_places"
    PUBLICATION_TYPES = "publication_types"
    SYSTEM_METADATA = "system_metadata"
    TRASH = "trash"

    @property
    def display_name(self) -> str:
        """Human-readable display name for the group."""
        return _GROUP_DISPLAY_NAMES[self]

    @property
    def include_in_gold(self) -> bool:
        """Whether fields in this group should be included in Gold layer."""
        return self not in (
            PublicationFieldGroup.TRASH,
            PublicationFieldGroup.SYSTEM_METADATA,
        )

    @classmethod
    def from_string(cls, value: str) -> PublicationFieldGroup:
        """Parse group from case-insensitive string value.

        Args:
            value: Group name string to parse (case-insensitive).

        Returns:
            Matching PublicationFieldGroup enum member.
        """
        normalized = value.lower().strip()
        try:
            return cls(normalized)
        except ValueError:
            valid = ", ".join(g.value for g in cls)
            raise ValueError(
                f"Invalid field group: '{value}'. Valid groups: {valid}"
            ) from None

    @classmethod
    def gold_groups(cls) -> tuple[PublicationFieldGroup, ...]:
        """Get all groups that should be included in Gold layer.

        Returns:
            Tuple of PublicationFieldGroup members included in Gold layer output.
        """
        return tuple(g for g in cls if g.include_in_gold)

    @classmethod
    def excluded_groups(cls) -> tuple[PublicationFieldGroup, ...]:
        """Get all groups excluded from Gold layer.

        Returns:
            Tuple of PublicationFieldGroup members excluded from Gold layer output.
        """
        return tuple(g for g in cls if not g.include_in_gold)


_GROUP_DISPLAY_NAMES: Final[dict[PublicationFieldGroup, str]] = {
    PublicationFieldGroup(key): value
    for key, value in GROUP_DISPLAY_NAMES_BY_VALUE.items()
}

FIELD_TO_GROUP_MAPPING: Final[dict[str, PublicationFieldGroup]] = {
    field_name: PublicationFieldGroup(group_value)
    for field_name, group_value in FIELD_TO_GROUP_VALUE_MAPPING.items()
}
