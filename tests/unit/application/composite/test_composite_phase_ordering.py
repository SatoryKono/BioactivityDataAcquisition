# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for composite phase ordering and dependency validation."""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)

pytestmark = pytest.mark.unit


def _publication_config(
    *, dependencies: tuple[DependencyConfig, ...]
) -> CompositeConfig:
    return CompositeConfig(
        name="publication_composite",
        version="1.0.0",
        seed=SeedConfig(
            pipeline="chembl_publication",
            output_keys=("publication_id", "doi"),
            silver_table="silver/chembl/publication",
        ),
        dependencies=dependencies,
        enrichers=(
            EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),
            EnricherConfig(pipeline="openalex_publication", join_keys=("doi",)),
        ),
        merge=MergeConfig(
            strategy="left_outer",
            conflict_resolution="seed_priority",
            output_silver_path="silver/composite/publication",
            output_gold_path="gold/composite/publication",
            sort_by_silver=("entity_id", "publication_id"),
        ),
    )


def test_validate_composite_config_rejects_duplicate_dependencies() -> None:
    """Dependency DAG must not contain duplicate pipeline identifiers."""
    with pytest.raises(ValueError, match="Duplicate dependency pipelines"):
        _publication_config(
            dependencies=(
                DependencyConfig(
                    pipeline="chembl_target",
                    join_keys=("publication_id",),
                    silver_table="silver/chembl/target",
                ),
                DependencyConfig(
                    pipeline="chembl_target",
                    join_keys=("publication_id",),
                    silver_table="silver/chembl/target",
                ),
            )
        )


def test_validate_composite_config_rejects_join_key_not_in_seed() -> None:
    """Enricher join keys must be declared on the seed output key set."""
    with pytest.raises(ValueError, match="join_key 'pmid'"):
        CompositeConfig(
            name="publication_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("publication_id", "doi"),
                silver_table="silver/chembl/publication",
            ),
            dependencies=(),
            enrichers=(
                EnricherConfig(pipeline="pubmed_publication", join_keys=("pmid",)),
            ),
            merge=MergeConfig(
                strategy="left_outer",
                conflict_resolution="seed_priority",
                output_silver_path="silver/composite/publication",
                output_gold_path="gold/composite/publication",
            ),
        )
