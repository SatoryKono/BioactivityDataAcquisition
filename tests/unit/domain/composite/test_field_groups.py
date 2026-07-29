# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for field group domain models.

Tests FieldMapping, FieldGroupDefinition, FieldGroupRegistry,
and build_field_group_registry.
"""

from __future__ import annotations

import pytest

from bioetl.domain.composite.field_groups import (
    DEFAULT_PROVIDER_ORDER,
    FieldGroupDefinition,
    FieldGroupId,
    FieldGroupRegistry,
    FieldMapping,
    build_field_group_registry,
)

pytestmark = pytest.mark.unit


# ============================================================
# FieldMapping Tests
# ============================================================


class TestFieldMapping:
    """Tests for FieldMapping dataclass."""

    def test_basic_creation(self) -> None:
        fm = FieldMapping(
            base_name="title",
            provider_columns=(
                "chembl.publication.title",
                "crossref.publication.title",
            ),
            group=FieldGroupId.BIBLIOGRAPHY,
        )
        assert fm.base_name == "title"
        assert len(fm.provider_columns) == 2
        assert fm.group == FieldGroupId.BIBLIOGRAPHY

    def test_providers_property(self) -> None:
        fm = FieldMapping(
            base_name="doi",
            provider_columns=(
                "chembl.publication.doi",
                "crossref.publication.doi",
                "openalex.publication.doi",
            ),
            group=FieldGroupId.ID_AND_STATUS,
        )
        assert fm.providers == ("chembl", "crossref", "openalex")

    def test_provider_count(self) -> None:
        fm = FieldMapping(
            base_name="doi",
            provider_columns=(
                "chembl.publication.doi",
                "pubmed.publication.doi",
            ),
            group=FieldGroupId.ID_AND_STATUS,
        )
        assert fm.provider_count == 2

    def test_has_provider(self) -> None:
        fm = FieldMapping(
            base_name="title",
            provider_columns=(
                "chembl.publication.title",
                "crossref.publication.title",
            ),
            group=FieldGroupId.BIBLIOGRAPHY,
        )
        assert fm.has_provider("chembl") is True
        assert fm.has_provider("CHEMBL") is True  # case-insensitive
        assert fm.has_provider("pubmed") is False

    def test_get_column(self) -> None:
        fm = FieldMapping(
            base_name="doi",
            provider_columns=(
                "chembl.publication.doi",
                "crossref.publication.doi",
            ),
            group=FieldGroupId.ID_AND_STATUS,
        )
        assert fm.get_column("chembl") == "chembl.publication.doi"
        assert fm.get_column("crossref") == "crossref.publication.doi"
        assert fm.get_column("pubmed") is None

    def test_empty_provider_columns(self) -> None:
        fm = FieldMapping(
            base_name="custom_field",
            group=FieldGroupId.TRASH,
        )
        assert fm.provider_columns == ()
        assert fm.providers == ()
        assert fm.provider_count == 0

    def test_groups_field_mapping__to_tuple_conversion__7f5ee31e(self) -> None:
        fm = FieldMapping(
            base_name="doi",
            provider_columns=["chembl.publication.doi"],  # type: ignore[arg-type]
            group=FieldGroupId.ID_AND_STATUS,
        )
        assert isinstance(fm.provider_columns, tuple)

    def test_empty_base_name_raises(self) -> None:
        with pytest.raises(ValueError, match="base_name cannot be empty"):
            FieldMapping(base_name="", group=FieldGroupId.BIBLIOGRAPHY)

    def test_default_group_is_trash(self) -> None:
        fm = FieldMapping(base_name="unknown_field")
        assert fm.group == FieldGroupId.TRASH

    def test_groups_field_mapping__frozen__c3aa795c(self) -> None:
        fm = FieldMapping(base_name="title", group=FieldGroupId.BIBLIOGRAPHY)
        with pytest.raises(AttributeError):
            fm.base_name = "other"  # type: ignore[misc]


# ============================================================
# FieldGroupDefinition Tests
# ============================================================


class TestFieldGroupDefinition:
    """Tests for FieldGroupDefinition dataclass."""

    def test_field_group_definition__basic_creation__cf5cf232(self) -> None:
        gd = FieldGroupDefinition(
            group_id=FieldGroupId.BIBLIOGRAPHY,
            display_name="Bibliography",
            include_in_gold=True,
            fields=(
                FieldMapping(
                    "title", ("chembl.publication.title",), FieldGroupId.BIBLIOGRAPHY
                ),
                FieldMapping(
                    "abstract",
                    ("chembl.publication.abstract",),
                    FieldGroupId.BIBLIOGRAPHY,
                ),
            ),
        )
        assert gd.group_id == FieldGroupId.BIBLIOGRAPHY
        assert gd.display_name == "Bibliography"
        assert gd.include_in_gold is True
        assert gd.field_count == 2

    def test_base_field_names(self) -> None:
        gd = FieldGroupDefinition(
            group_id=FieldGroupId.BIBLIOGRAPHY,
            display_name="Bibliography",
            fields=(
                FieldMapping("title", (), FieldGroupId.BIBLIOGRAPHY),
                FieldMapping("abstract", (), FieldGroupId.BIBLIOGRAPHY),
                FieldMapping("journal", (), FieldGroupId.BIBLIOGRAPHY),
            ),
        )
        assert gd.base_field_names == ("title", "abstract", "journal")

    def test_all_columns(self) -> None:
        gd = FieldGroupDefinition(
            group_id=FieldGroupId.BIBLIOGRAPHY,
            display_name="Bibliography",
            fields=(
                FieldMapping(
                    "title",
                    ("chembl.publication.title", "crossref.publication.title"),
                    FieldGroupId.BIBLIOGRAPHY,
                ),
                FieldMapping(
                    "abstract",
                    ("chembl.publication.abstract",),
                    FieldGroupId.BIBLIOGRAPHY,
                ),
            ),
        )
        assert gd.all_columns == (
            "chembl.publication.title",
            "crossref.publication.title",
            "chembl.publication.abstract",
        )

    def test_empty_fields(self) -> None:
        gd = FieldGroupDefinition(
            group_id=FieldGroupId.TRASH,
            display_name="Trash",
            include_in_gold=False,
        )
        assert gd.fields == ()
        assert gd.field_count == 0
        assert gd.base_field_names == ()
        assert gd.all_columns == ()

    def test_field_group_definition__to_tuple_conversion__90fc8878(self) -> None:
        gd = FieldGroupDefinition(
            group_id=FieldGroupId.BIBLIOGRAPHY,
            display_name="Bibliography",
            fields=[  # type: ignore[arg-type]
                FieldMapping("title", (), FieldGroupId.BIBLIOGRAPHY),
            ],
        )
        assert isinstance(gd.fields, tuple)


# ============================================================
# FieldGroupRegistry Tests
# ============================================================


def _build_test_registry() -> FieldGroupRegistry:
    """Build a test registry with representative groups."""
    return build_field_group_registry(
        groups=(
            FieldGroupDefinition(
                group_id=FieldGroupId.ID_AND_STATUS,
                display_name="ID & Status",
                include_in_gold=True,
                fields=(
                    FieldMapping(
                        "doi",
                        (
                            "chembl.publication.doi",
                            "crossref.publication.doi",
                            "openalex.publication.doi",
                        ),
                        FieldGroupId.ID_AND_STATUS,
                    ),
                    FieldMapping(
                        "pmid",
                        (
                            "chembl.publication.pmid",
                            "pubmed.publication.pmid",
                        ),
                        FieldGroupId.ID_AND_STATUS,
                    ),
                ),
            ),
            FieldGroupDefinition(
                group_id=FieldGroupId.BIBLIOGRAPHY,
                display_name="Bibliography",
                include_in_gold=True,
                fields=(
                    FieldMapping(
                        "title",
                        (
                            "chembl.publication.title",
                            "crossref.publication.title",
                        ),
                        FieldGroupId.BIBLIOGRAPHY,
                    ),
                    FieldMapping(
                        "abstract",
                        ("chembl.publication.abstract",),
                        FieldGroupId.BIBLIOGRAPHY,
                    ),
                ),
            ),
            FieldGroupDefinition(
                group_id=FieldGroupId.TRASH,
                display_name="Trash",
                include_in_gold=False,
                fields=(
                    FieldMapping(
                        "content_hash",
                        (
                            "chembl.publication.content_hash",
                            "crossref.publication.content_hash",
                        ),
                        FieldGroupId.TRASH,
                    ),
                    FieldMapping(
                        "language",
                        ("crossref.publication.language",),
                        FieldGroupId.TRASH,
                    ),
                ),
            ),
        ),
        provider_order=DEFAULT_PROVIDER_ORDER,
    )


class TestFieldGroupRegistry:
    """Tests for FieldGroupRegistry."""

    def test_get_group_qualified_column(self) -> None:
        registry = _build_test_registry()
        assert (
            registry.get_group("chembl.publication.doi") == FieldGroupId.ID_AND_STATUS
        )
        assert (
            registry.get_group("crossref.publication.title")
            == FieldGroupId.BIBLIOGRAPHY
        )
        assert (
            registry.get_group("crossref.publication.content_hash")
            == FieldGroupId.TRASH
        )

    def test_get_group_unqualified(self) -> None:
        registry = _build_test_registry()
        assert registry.get_group("doi") == FieldGroupId.ID_AND_STATUS
        assert registry.get_group("title") == FieldGroupId.BIBLIOGRAPHY
        assert registry.get_group("content_hash") == FieldGroupId.TRASH

    def test_get_group_unknown_defaults_to_trash(self) -> None:
        registry = _build_test_registry()
        assert registry.get_group("unknown_field") == FieldGroupId.TRASH

    def test_get_group_case_insensitive(self) -> None:
        registry = _build_test_registry()
        assert registry.get_group("DOI") == FieldGroupId.ID_AND_STATUS
        assert registry.get_group("Title") == FieldGroupId.BIBLIOGRAPHY
        assert (
            registry.get_group("CHEMBL.PUBLICATION.DOI") == FieldGroupId.ID_AND_STATUS
        )

    def test_is_gold_field(self) -> None:
        registry = _build_test_registry()
        assert registry.is_gold_field("doi") is True
        assert registry.is_gold_field("title") is True
        assert registry.is_gold_field("content_hash") is False
        assert registry.is_gold_field("language") is False

    def test_get_gold_columns(self) -> None:
        registry = _build_test_registry()
        columns = [
            "chembl.publication.doi",
            "chembl.publication.title",
            "chembl.publication.content_hash",
            "_run_id",
        ]
        gold = registry.get_gold_columns(columns)
        assert "chembl.publication.doi" in gold
        assert "chembl.publication.title" in gold
        assert "_run_id" in gold  # system columns always included
        assert "chembl.publication.content_hash" not in gold

    def test_get_trash_columns(self) -> None:
        registry = _build_test_registry()
        columns = [
            "chembl.publication.doi",
            "chembl.publication.content_hash",
            "crossref.publication.language",
            "_run_id",
        ]
        trash = registry.get_trash_columns(columns)
        assert "chembl.publication.content_hash" in trash
        assert "crossref.publication.language" in trash
        assert "chembl.publication.doi" not in trash
        assert "_run_id" not in trash  # system columns excluded from trash

    def test_get_columns_by_group(self) -> None:
        registry = _build_test_registry()
        columns = [
            "chembl.publication.doi",
            "chembl.publication.pmid",
            "chembl.publication.title",
            "chembl.publication.content_hash",
        ]
        id_cols = registry.get_columns_by_group(columns, FieldGroupId.ID_AND_STATUS)
        assert "chembl.publication.doi" in id_cols
        assert "chembl.publication.pmid" in id_cols
        assert "chembl.publication.title" not in id_cols

    def test_field_group_registry__get_ordered_columns__c06bdded(self) -> None:
        registry = _build_test_registry()
        columns = [
            "chembl.publication.title",
            "crossref.publication.content_hash",
            "chembl.publication.doi",
            "_run_id",
            "crossref.publication.title",
        ]
        ordered = registry.get_ordered_columns(columns)

        # ID_AND_STATUS should come before BIBLIOGRAPHY
        doi_idx = ordered.index("chembl.publication.doi")
        title_idx = ordered.index("chembl.publication.title")
        assert doi_idx < title_idx

        # Within BIBLIOGRAPHY, chembl before crossref (provider order)
        chembl_title_idx = ordered.index("chembl.publication.title")
        crossref_title_idx = ordered.index("crossref.publication.title")
        assert chembl_title_idx < crossref_title_idx

        # System columns at the end
        assert ordered[-1] == "_run_id"

        # Trash at the end of data columns (before system)
        content_hash_idx = ordered.index("crossref.publication.content_hash")
        assert content_hash_idx > crossref_title_idx

    def test_validate_columns(self) -> None:
        registry = _build_test_registry()
        columns = [
            "chembl.publication.doi",
            "chembl.publication.title",
            "unknown_field",
            "_run_id",
        ]
        result = registry.validate_columns(columns)
        assert "chembl.publication.doi" in result["mapped"]
        assert "chembl.publication.title" in result["mapped"]
        assert "unknown_field" in result["unmapped"]
        assert "_run_id" in result["system"]

    def test_get_field_mapping(self) -> None:
        registry = _build_test_registry()
        mapping = registry.get_field_mapping("doi")
        assert mapping is not None
        assert mapping.base_name == "doi"
        assert mapping.provider_count == 3

    def test_get_field_mapping_not_found(self) -> None:
        registry = _build_test_registry()
        assert registry.get_field_mapping("unknown") is None

    def test_get_group_definition(self) -> None:
        registry = _build_test_registry()
        gd = registry.get_group_definition(FieldGroupId.BIBLIOGRAPHY)
        assert gd is not None
        assert gd.display_name == "Bibliography"
        assert gd.field_count == 2

    def test_get_group_definition_not_found(self) -> None:
        registry = _build_test_registry()
        # AUTHOR_AND_AFFILIATIONS not in test registry
        assert (
            registry.get_group_definition(FieldGroupId.AUTHOR_AND_AFFILIATIONS) is None
        )

    def test_field_count(self) -> None:
        registry = _build_test_registry()
        # doi, pmid, title, abstract, content_hash, language = 6 base fields
        assert registry.field_count == 6

    def test_column_count(self) -> None:
        registry = _build_test_registry()
        # doi:3 + pmid:2 + title:2 + abstract:1 + content_hash:2 + language:1 = 11
        assert registry.column_count == 11

    def test_provider_order(self) -> None:
        registry = _build_test_registry()
        assert registry.provider_order == DEFAULT_PROVIDER_ORDER

    def test_groups_property(self) -> None:
        registry = _build_test_registry()
        assert len(registry.groups) == 3


# ============================================================
# build_field_group_registry Tests
# ============================================================


class TestBuildFieldGroupRegistry:
    """Tests for build_field_group_registry factory."""

    def test_creates_registry(self) -> None:
        registry = build_field_group_registry(
            groups=(
                FieldGroupDefinition(
                    group_id=FieldGroupId.BIBLIOGRAPHY,
                    display_name="Bibliography",
                    fields=(FieldMapping("title", (), FieldGroupId.BIBLIOGRAPHY),),
                ),
            ),
        )
        assert isinstance(registry, FieldGroupRegistry)
        assert registry.field_count == 1

    def test_custom_provider_order(self) -> None:
        registry = build_field_group_registry(
            groups=(),
            provider_order=("pubmed", "chembl"),
        )
        assert registry.provider_order == ("pubmed", "chembl")

    def test_custom_default_group(self) -> None:
        registry = build_field_group_registry(
            groups=(),
            default_group=FieldGroupId.BIBLIOGRAPHY,
        )
        # Unknown fields should now default to BIBLIOGRAPHY
        assert registry.get_group("unknown") == FieldGroupId.BIBLIOGRAPHY

    def test_empty_groups(self) -> None:
        registry = build_field_group_registry(groups=())
        assert registry.field_count == 0
        assert registry.column_count == 0
        assert registry.get_group("any_field") == FieldGroupId.TRASH


# ============================================================
# FieldGroupId (re-export alias) Tests
# ============================================================


class TestFieldGroupId:
    """Tests for FieldGroupId alias."""

    def test_is_publication_field_group(self) -> None:
        from bioetl.domain.value_objects.publication_field_group_types import (
            PublicationFieldGroup,
        )

        assert FieldGroupId is PublicationFieldGroup

    def test_groups_field_group_id__enum_values__f411e47f(self) -> None:
        assert FieldGroupId.ID_AND_STATUS.value == "id_and_status"
        assert FieldGroupId.BIBLIOGRAPHY.value == "bibliography"
        assert FieldGroupId.TRASH.value == "trash"

    def test_include_in_gold(self) -> None:
        assert FieldGroupId.BIBLIOGRAPHY.include_in_gold is True
        assert FieldGroupId.TRASH.include_in_gold is False
        assert FieldGroupId.SYSTEM_METADATA.include_in_gold is False

    def test_gold_groups(self) -> None:
        gold = FieldGroupId.gold_groups()
        assert FieldGroupId.TRASH not in gold
        assert FieldGroupId.SYSTEM_METADATA not in gold
        assert FieldGroupId.BIBLIOGRAPHY in gold
        assert len(gold) == 7  # All groups except TRASH and SYSTEM_METADATA
