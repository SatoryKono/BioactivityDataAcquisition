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
"""Unit scenario for the composite_assay pipeline.

The executed pipeline is ``composite_assay``. ``chembl_assay`` is only the seed.
"""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.infrastructure.config import load_composite_config

pytestmark = pytest.mark.unit

_EXECUTED_PIPELINE = "composite_assay"


def test_composite_assay_config_executes_composite_pipeline() -> None:
    """Loading ``assay`` runs the composite_assay contract, not chembl_assay."""
    config = load_composite_config("assay")

    assert config.name == _EXECUTED_PIPELINE
    assert config.seed.pipeline == "chembl_assay"
    assert config.seed.silver_table == "silver/chembl/assay"
    assert config.dependencies == ()
    assert config.merge.strategy == MergeStrategy.LEFT_OUTER
    assert config.optional_enrichers == ("chembl_cell_line", "chembl_tissue")
    assert config.required_enrichers == ()

    cell_line = config.get_enricher("chembl_cell_line")
    tissue = config.get_enricher("chembl_tissue")
    assert cell_line is not None
    assert tissue is not None
    assert cell_line.join_keys == ("cell_id",)
    assert tissue.join_keys == ("tissue_id",)
    assert cell_line.required is False
    assert tissue.required is False


def test_optional_cell_line_enricher_keeps_assays_without_cell() -> None:
    """Left-outer cell enrichment preserves assays that have no cell line."""
    config = load_composite_config("assay")
    assert config.name == "composite_assay"
    cell_line = config.get_enricher("chembl_cell_line")
    assert cell_line is not None
    join_key = cell_line.join_keys[0]

    assays = pl.DataFrame(
        {
            "assay_id": ["CHEMBL1", "CHEMBL2"],
            join_key: ["CL1", None],
        }
    )
    cells = pl.DataFrame(
        {
            join_key: ["CL1"],
            "cell_name": ["HEK293"],
        }
    )

    result = assays.join(cells, on=join_key, how="left")

    assert result.height == 2
    missing = result.filter(pl.col("assay_id") == "CHEMBL2")
    assert missing["cell_name"][0] is None
