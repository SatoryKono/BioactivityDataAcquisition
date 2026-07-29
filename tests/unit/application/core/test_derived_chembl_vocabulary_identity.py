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
"""Golden identity tests for derived ChEMBL vocabulary entities."""

from __future__ import annotations

import pytest

from bioetl.application.core.entity_id import (
    compute_publication_term_entity_id,
    compute_subcellular_fraction_entity_id,
)
from bioetl.application.core.publication_term_runtime import create_term_record
from bioetl.domain.normalization.profiles import (
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_PUBLICATION_TERM_PROFILE,
    CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
)


pytestmark = pytest.mark.unit


def test_subcellular_fraction_identity_matches_source_and_derived_profiles() -> None:
    """Assay-derived subcellular fraction IDs must use the same canonical value."""
    source_rule = CHEMBL_ASSAY_PROFILE.rule_for("assay_subcellular_fraction")
    derived_rule = CHEMBL_SUBCELLULAR_FRACTION_PROFILE.rule_for("subcellular_fraction")

    assert source_rule is not None
    assert derived_rule is not None

    source_value = source_rule.apply("  microsomes  ")
    derived_value = derived_rule.apply("Microsomes")

    assert source_value == derived_value == "Microsomes"
    assert compute_subcellular_fraction_entity_id("  microsomes  ") == (
        compute_subcellular_fraction_entity_id("Microsomes")
    )


def test_publication_term_identity_matches_runtime_record_and_profile_surface() -> None:
    """Publication-term IDs must stay aligned with the derived normalized term surface."""
    term_rule = CHEMBL_PUBLICATION_TERM_PROFILE.rule_for("term")
    term_type_rule = CHEMBL_PUBLICATION_TERM_PROFILE.rule_for("term_type")

    assert term_rule is not None
    assert term_type_rule is not None

    record = create_term_record(
        publication_id="CHEMBL12345",
        term="  apoptosis  ",
        term_type="keyword",
        mesh_id=None,
        qualifier=None,
    )

    normalized_term = term_rule.apply(record["term"])
    normalized_term_type = term_type_rule.apply(record["term_type"])

    assert normalized_term == "apoptosis"
    assert normalized_term_type == "KEYWORD"
    assert record["entity_id"] == compute_publication_term_entity_id(
        "CHEMBL12345",
        "keyword",
        "  apoptosis  ",
    )


def test_publication_term_mesh_heading_and_qualifier_ids_are_stable() -> None:
    """Different term types must keep deterministic composite-key identity."""
    heading = create_term_record(
        publication_id="CHEMBL67890",
        term="Cancer",
        term_type="MESH_HEADING",
        mesh_id="D009369",
        qualifier=None,
    )
    qualifier = create_term_record(
        publication_id="CHEMBL67890",
        term="therapy",
        term_type="MESH_QUALIFIER",
        mesh_id="D009369",
        qualifier=None,
    )

    assert heading["entity_id"] != qualifier["entity_id"]
    assert heading["entity_id"] == compute_publication_term_entity_id(
        "CHEMBL67890",
        "MESH_HEADING",
        "Cancer",
    )
