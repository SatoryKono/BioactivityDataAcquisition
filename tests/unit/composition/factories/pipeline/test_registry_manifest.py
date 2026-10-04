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
"""Unit tests for the declarative registry manifest assembly seam."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.composition.factories.pipeline._registry_manifest_chembl import (
    CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline._registry_manifest_non_chembl import (
    NON_CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig
from bioetl.composition.factories.pipeline.registry_manifest import (
    PIPELINE_CONFIGS,
)


@pytest.mark.unit
def test_pipeline_identity_preserves_full_entity_and_explicit_bindings() -> None:
    gold, silver, pandera = object(), object(), object()
    config = PipelineFactoryConfig.for_pipeline(
        "chembl_target_protein_classification",
        transformer_class="explicit.module.Transformer",
        silver_schema=silver,
        gold_schema=gold,
        pandera_silver_schema=pandera,
        data_source_provider="custom_source",
    )
    assert (config.provider, config.entity_type) == (
        "chembl",
        "target_protein_classification",
    )
    assert config.transformer_class == "explicit.module.Transformer"
    assert config.silver_schema is silver
    assert config.gold_schema is gold
    assert config.pandera_silver_schema is pandera
    assert config.data_source_provider == "custom_source"


@pytest.mark.unit
@pytest.mark.parametrize("name", ["", "chembl", "_activity", "chembl_"])
def test_pipeline_identity_rejects_missing_components(name: str) -> None:
    with pytest.raises(ValueError, match="provider and entity"):
        PipelineFactoryConfig.for_pipeline(
            name,
            transformer_class="module.Transformer",
            silver_schema=None,
            gold_schema=object(),
        )


@pytest.mark.unit
def test_registry_manifest_concatenates_prebuilt_pipeline_factory_configs() -> None:
    """The manifest should only concatenate already prepared config tuples."""
    assert PIPELINE_CONFIGS == (
        *CHEMBL_PIPELINE_CONFIGS,
        *NON_CHEMBL_PIPELINE_CONFIGS,
    )
    assert all(isinstance(config, PipelineFactoryConfig) for config in PIPELINE_CONFIGS)


@pytest.mark.unit
def test_registry_manifest_has_no_runtime_calls_or_local_builders() -> None:
    """The manifest should not do loading, normalization, or local construction."""
    source = Path(
        "src/bioetl/composition/factories/pipeline/registry_manifest.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    called_functions = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called_functions <= {"tuple"}, (
        "registry_manifest.py should not construct or load configs at runtime:\n"
        + "\n".join(sorted(called_functions))
    )

    local_defs = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    assert not local_defs, (
        "registry_manifest.py should not define local logic:\n"
        + "\n".join(sorted(local_defs))
    )
