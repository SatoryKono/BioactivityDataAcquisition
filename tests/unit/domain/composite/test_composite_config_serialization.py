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
"""Regression snapshots for CompositeConfig serialization."""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


pytestmark = pytest.mark.unit


def _build_composite_config() -> CompositeConfig:
    return CompositeConfig(
        name="composite_publication",
        version="1.0.0",
        seed=SeedConfig(
            pipeline="chembl_publication",
            output_keys=("doi", "pmid"),
            silver_table="silver/chembl/publication",
        ),
        dependencies=(
            DependencyConfig(
                pipeline="chembl_document",
                join_keys=("doi",),
                required=False,
                timeout_seconds=600,
                silver_table="silver/chembl/document",
                filter_fields=("doi",),
            ),
        ),
        enrichers=(
            EnricherConfig(
                pipeline="crossref_publication",
                join_keys=("doi",),
                required=True,
                timeout_seconds=900,
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/composite/publication",
            output_gold_path="gold/composite/publication",
            sort_by_silver=("doi",),
            sort_by_gold=("doi",),
        ),
    )


def test_composite_config_to_dict_snapshot() -> None:
    config = _build_composite_config()
    payload = config.to_dict()

    assert payload["name"] == "composite_publication"
    assert payload["version"] == "1.0.0"
    assert payload["seed"] == {
        "pipeline": "chembl_publication",
        "output_keys": ["doi", "pmid"],
        "silver_table": "silver/chembl/publication",
        "limit": None,
    }
    assert payload["dependencies"][0]["pipeline"] == "chembl_document"
    assert payload["dependencies"][0]["filter_fields"] == ["doi"]
    assert payload["enrichers"][0]["pipeline"] == "crossref_publication"
    assert payload["enrichers"][0]["timeout_seconds"] == 900
    assert payload["enrichers"][0]["cardinality"] == "one_to_one"
    assert payload["merge"]["strategy"] == "left_outer"
    assert payload["merge"]["sort_by_silver"] == ["doi"]
    assert payload["merge"]["preserve_all_sources"] is False
    # Lossless surface includes top-level runtime blocks.
    assert set(payload) >= {
        "dq",
        "execution",
        "lineage",
        "cross_validation",
        "merge",
        "seed",
        "enrichers",
        "dependencies",
    }


def test_composite_config_from_dict_roundtrip_snapshot() -> None:
    original = _build_composite_config()
    serialized = original.to_dict()

    restored = CompositeConfig.from_dict(serialized)

    assert restored.to_dict() == serialized
    assert restored.name == original.name
    assert restored.version == original.version
    assert restored.seed.output_keys == original.seed.output_keys
    assert restored.merge.strategy == original.merge.strategy
    assert restored.merge.conflict_resolution == original.merge.conflict_resolution
