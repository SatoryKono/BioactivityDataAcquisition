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
"""Regression tests for the split UniProt comment facet barrel."""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.uniprot.extractors import _comment_facets
from bioetl.application.pipelines.uniprot.extractors._comment_facets_data import (
    _COMMENT_ANNOTATION_OUTPUT_KEYS,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_all import (
    extract_all_comments,
    extract_all_comments_raw,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    count_isoforms,
    extract_alternative_products,
    extract_biophysicochemical_properties,
    extract_by_type,
    extract_catalytic_activity,
    extract_cofactors,
    extract_isoform_details,
    extract_reaction_ec_numbers,
    extract_reactions,
    extract_subcellular_locations,
    extract_text_values,
)


pytestmark = pytest.mark.unit


def test_comment_facets_barrel_preserves_split_helper_exports() -> None:
    """Comment facet barrel should stay a thin export surface over split helpers."""
    assert _comment_facets.count_isoforms is count_isoforms
    assert _comment_facets.extract_all_comments is extract_all_comments
    assert _comment_facets.extract_all_comments_raw is extract_all_comments_raw
    assert _comment_facets.extract_alternative_products is extract_alternative_products
    assert (
        _comment_facets.extract_biophysicochemical_properties
        is extract_biophysicochemical_properties
    )
    assert _comment_facets.extract_by_type is extract_by_type
    assert _comment_facets.extract_catalytic_activity is extract_catalytic_activity
    assert _comment_facets.extract_cofactors is extract_cofactors
    assert _comment_facets.extract_isoform_details is extract_isoform_details
    assert _comment_facets.extract_reaction_ec_numbers is extract_reaction_ec_numbers
    assert _comment_facets.extract_reactions is extract_reactions
    assert (
        _comment_facets.extract_subcellular_locations is extract_subcellular_locations
    )
    assert _comment_facets.extract_text_values is extract_text_values
    assert set(_comment_facets.__all__) == {
        "count_isoforms",
        "extract_all_comments",
        "extract_all_comments_raw",
        "extract_alternative_products",
        "extract_biophysicochemical_properties",
        "extract_by_type",
        "extract_catalytic_activity",
        "extract_cofactors",
        "extract_isoform_details",
        "extract_reaction_ec_numbers",
        "extract_reactions",
        "extract_subcellular_locations",
        "extract_text_values",
    }


def test_comment_annotation_keys_are_extractor_outputs() -> None:
    """Transformer annotation keys must stay backed by comment extractor output."""
    comment_data = extract_all_comments(None)

    assert set(_COMMENT_ANNOTATION_OUTPUT_KEYS) <= set(comment_data)
    assert "isoform_count" not in _COMMENT_ANNOTATION_OUTPUT_KEYS
