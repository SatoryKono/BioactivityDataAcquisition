"""Additional branch coverage tests for domain composite config models."""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config import (
    ColumnGroupConfig,
    CompositeConfig,
    CompositeDQConfig,
    CrossValidationConfig,
    DependencyConfig,
    EnricherConfig,
    ExecutionConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.config import CrossFieldValidation, FieldValidation
from bioetl.domain.composite.config_validators import (
    _validate_optional_threshold,
    _validate_positive,
    _validate_threshold_order,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


def _seed() -> SeedConfig:
    return SeedConfig(
        pipeline="chembl_publication",
        output_keys=("doi", "pmid"),
        silver_table="silver/chembl/publication",
    )


def _merge() -> MergeConfig:
    return MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/publication",
        output_gold_path="gold/composite/publication",
    )


def test_dependency_config_converts_lists_and_resolves_filters() -> None:
    dependency = DependencyConfig(
        pipeline="chembl_document",
        join_keys=["document_chembl_id"],  # type: ignore[arg-type]
        filter_fields=["document_chembl_id", "molecule_chembl_id"],  # type: ignore[arg-type]
        silver_table="silver/chembl/document",
    )

    assert dependency.primary_join_key == "document_chembl_id"
    assert dependency.effective_filter_fields == (
        "document_chembl_id",
        "molecule_chembl_id",
    )
    assert dependency.is_multi_field_filter is True


def test_dependency_config_uses_filter_field_fallback_chain() -> None:
    dependency = DependencyConfig(
        pipeline="chembl_document",
        join_keys=("document_chembl_id",),
        filter_field="doc_id",
        silver_table="silver/chembl/document",
    )

    assert dependency.effective_filter_fields == ("doc_id",)
    assert dependency.uses_seed_keys is True


def test_dependency_config_validates_filter_field_exclusive() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        DependencyConfig(
            pipeline="chembl_document",
            join_keys=("document_chembl_id",),
            filter_field="doc_id",
            filter_fields=("doc_id",),
            silver_table="silver/chembl/document",
        )


def test_enricher_config_converts_join_keys_list() -> None:
    enricher = EnricherConfig(
        pipeline="crossref_publication",
        join_keys=["doi"],  # type: ignore[arg-type]
    )

    assert enricher.join_keys == ("doi",)


def test_layer_column_config_converts_non_dict_rename_fields() -> None:
    config = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/test",
        output_gold_path="gold/test",
        column_groups=[{"name": "ids", "fields": ["doi"]}],  # type: ignore[arg-type]
        exclude_fields=["_dq_*"],  # type: ignore[arg-type]
    )

    assert config.column_groups[0].name == "ids"
    assert config.exclude_fields == ("_dq_*",)


def test_column_group_requires_fields_or_pattern() -> None:
    with pytest.raises(ValueError, match="must have either fields or pattern"):
        ColumnGroupConfig(name="empty")


def test_merge_config_requires_non_empty_output_paths() -> None:
    with pytest.raises(ValueError, match="output_silver_path cannot be empty"):
        MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="",
            output_gold_path="gold/test",
        )
    with pytest.raises(ValueError, match="output_gold_path cannot be empty"):
        MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/test",
            output_gold_path="",
        )


def test_composite_dq_config_validates_ranges_and_required_fields_list() -> None:
    config = CompositeDQConfig(
        soft_fail_threshold=0.1,
        hard_fail_threshold=0.3,
        required_fields=["title"],  # type: ignore[arg-type]
        field_validations=[
            FieldValidation(field="title", validation_type="required", nullable=False)
        ],  # type: ignore[arg-type]
        cross_field_validations=[
            CrossFieldValidation(
                name="publication_identity_anchor",
                fields=["doi", "pmid", "title"],  # type: ignore[arg-type]
                condition="any_present",
            )
        ],  # type: ignore[arg-type]
    )
    assert config.required_fields == ("title",)
    assert config.field_validations[0].field == "title"
    assert config.cross_field_validations[0].fields == ("doi", "pmid", "title")

    with pytest.raises(ValueError, match="soft_fail_threshold must be between"):
        CompositeDQConfig(soft_fail_threshold=1.2, hard_fail_threshold=1.3)
    with pytest.raises(ValueError, match="hard_fail_threshold must be between"):
        CompositeDQConfig(soft_fail_threshold=0.1, hard_fail_threshold=-0.1)


def test_execution_config_validation_branches() -> None:
    with pytest.raises(ValueError, match="max_concurrency must be positive"):
        ExecutionConfig(max_concurrency=0)
    with pytest.raises(ValueError, match="retry_max_attempts must be non-negative"):
        ExecutionConfig(retry_max_attempts=-1)
    with pytest.raises(ValueError, match="retry_backoff_multiplier must be positive"):
        ExecutionConfig(retry_backoff_multiplier=0.0)


def test_cross_validation_config_validation_branches() -> None:
    config = CrossValidationConfig(enricher_pairings=[])  # type: ignore[arg-type]
    assert config.enricher_pairings == ()

    with pytest.raises(ValueError, match="warning_threshold must be >= 1"):
        CrossValidationConfig(warning_threshold=0)
    with pytest.raises(ValueError, match="error_threshold must be >= 2"):
        CrossValidationConfig(error_threshold=1)
    with pytest.raises(ValueError, match="warning_threshold must be < error_threshold"):
        CrossValidationConfig(warning_threshold=2, error_threshold=2)
    with pytest.raises(ValueError, match="quarantine_threshold must be >= 1"):
        CrossValidationConfig(quarantine_threshold=0)
    with pytest.raises(ValueError, match="fuzzy_threshold must be in"):
        CrossValidationConfig(fuzzy_threshold=0.0)
    with pytest.raises(ValueError, match="numeric_tolerance must be in"):
        CrossValidationConfig(numeric_tolerance=0.0)


def test_composite_config_converts_lists_and_validates_required_fields() -> None:
    base_enricher = EnricherConfig(pipeline="crossref_publication", join_keys=("doi",))
    base_dep = DependencyConfig(
        pipeline="chembl_document",
        join_keys=("doi",),
        silver_table="silver/chembl/document",
    )

    config = CompositeConfig(
        name="composite_publication",
        version="1.0.0",
        seed=_seed(),
        enrichers=[base_enricher],  # type: ignore[arg-type]
        dependencies=[base_dep],  # type: ignore[arg-type]
        merge=_merge(),
    )

    assert config.all_enricher_names == ("crossref_publication",)
    assert config.all_dependency_names == ("chembl_document",)
    assert config.required_dependencies == ()
    assert config.optional_dependencies == ("chembl_document",)
    assert config.get_dependency("chembl_document") is not None
    assert config.get_dependency("missing") is None


def test_composite_config_validates_empty_name_version_and_sources() -> None:
    with pytest.raises(ValueError, match="composite name cannot be empty"):
        CompositeConfig(
            name="",
            version="1.0.0",
            seed=_seed(),
            enrichers=(EnricherConfig(pipeline="e", join_keys=("doi",)),),
            merge=_merge(),
        )
    with pytest.raises(ValueError, match="composite version cannot be empty"):
        CompositeConfig(
            name="composite_publication",
            version="",
            seed=_seed(),
            enrichers=(EnricherConfig(pipeline="e", join_keys=("doi",)),),
            merge=_merge(),
        )
    with pytest.raises(ValueError, match="at least one enricher or dependency"):
        CompositeConfig(
            name="composite_publication",
            version="1.0.0",
            seed=_seed(),
            enrichers=(),
            dependencies=(),
            merge=_merge(),
        )


def test_composite_config_dependency_key_validation_and_chained_skip() -> None:
    # Chained dependency: join keys are not validated against seed keys.
    chained = CompositeConfig(
        name="composite_publication",
        version="1.0.0",
        seed=_seed(),
        enrichers=(),
        dependencies=(
            DependencyConfig(
                pipeline="chembl_protein_class",
                join_keys=("protein_classification_id",),
                key_source="chembl_target_component",
                silver_table="silver/chembl/protein_class",
            ),
        ),
        merge=_merge(),
    )
    assert chained.dependencies[0].uses_seed_keys is False

    # Seed-key dependency with missing join key must fail.
    with pytest.raises(
        ValueError, match="Dependency chembl_document join_key 'document_id'"
    ):
        CompositeConfig(
            name="composite_publication",
            version="1.0.0",
            seed=_seed(),
            enrichers=(),
            dependencies=(
                DependencyConfig(
                    pipeline="chembl_document",
                    join_keys=("document_id",),
                    silver_table="silver/chembl/document",
                ),
            ),
            merge=_merge(),
        )


def test_composite_config_validates_duplicate_dependencies() -> None:
    dep = DependencyConfig(
        pipeline="chembl_document",
        join_keys=("doi",),
        silver_table="silver/chembl/document",
    )
    with pytest.raises(ValueError, match="Duplicate dependency pipelines"):
        CompositeConfig(
            name="composite_publication",
            version="1.0.0",
            seed=_seed(),
            enrichers=(),
            dependencies=(dep, dep),
            merge=_merge(),
        )


def test_validation_helpers_raise_on_invalid_values() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        _validate_positive(0, "timeout")
    with pytest.raises(ValueError, match=r"must be between 0\.0 and 1\.0"):
        _validate_optional_threshold(1.2, "soft_fail_threshold")
    with pytest.raises(ValueError, match="soft_fail_threshold must be less than"):
        _validate_threshold_order(0.5, 0.5)
