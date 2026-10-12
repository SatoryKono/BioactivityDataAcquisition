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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Publication identifier profile regression coverage."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.domain.mapping.publication_type_classification import (
    classify_publication_type,
)
from bioetl.domain.normalization.profiles.crossref_publication import (
    CROSSREF_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.openalex_publication import (
    OPENALEX_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.pubchem_compound import (
    PUBCHEM_COMPOUND_PROFILE,
)
from bioetl.domain.normalization.profiles.pubmed_publication import (
    PUBMED_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.semanticscholar_publication import (
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
)
from tests.helpers.publication_type_classification import (
    initialize_test_publication_type_classification,
)

pytestmark = pytest.mark.repo_backed


def test_crossref_profile_canonicalizes_issn_collection_fields() -> None:
    issn_rule = CROSSREF_PUBLICATION_PROFILE.rule_for("issn")
    issn_list_rule = CROSSREF_PUBLICATION_PROFILE.rule_for("issn_list")
    issn_print_rule = CROSSREF_PUBLICATION_PROFILE.rule_for("issn_print")
    issn_electronic_rule = CROSSREF_PUBLICATION_PROFILE.rule_for("issn_electronic")

    assert issn_rule is not None
    assert issn_list_rule is not None
    assert issn_print_rule is not None
    assert issn_electronic_rule is not None

    assert issn_rule.apply(" ISSN:1234567X ") == "1234-567X"
    assert (
        issn_list_rule.apply(["2049-3630", "ISSN:1234567X"])
        == '["1234-567X","2049-3630"]'
    )
    assert issn_print_rule.apply("issn:1234567x") == "1234-567X"
    assert issn_electronic_rule.apply("20493630") == "2049-3630"


def test_openalex_and_semanticscholar_profiles_canonicalize_pmid_strings() -> None:
    for profile in (
        OPENALEX_PUBLICATION_PROFILE,
        SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    ):
        pmid_rule = profile.rule_for("pmid")
        publication_pmid_rule = profile.rule_for("publication_pmid")
        assert pmid_rule is not None
        assert publication_pmid_rule is not None
        assert pmid_rule.apply(" PMID:0012345 ") == "12345"
        assert publication_pmid_rule.apply(12345) == "12345"


def test_pubchem_profile_canonicalizes_cid_before_identity_boundaries() -> None:
    molecule_id_rule = PUBCHEM_COMPOUND_PROFILE.rule_for("molecule_id")

    assert molecule_id_rule is not None
    assert molecule_id_rule.apply(" CID:2244 ") == "2244"


def test_publication_taxonomy_fixture_cases_match_profile_rules() -> None:
    initialize_test_publication_type_classification()
    payload = yaml.safe_load(
        Path("tests/fixtures/normalization/non_chembl_identifier_cases.yaml").read_text(
            encoding="utf-8"
        )
    )
    profiles = {
        "crossref.publication": CROSSREF_PUBLICATION_PROFILE,
        "openalex.publication": OPENALEX_PUBLICATION_PROFILE,
        "pubmed.publication": PUBMED_PUBLICATION_PROFILE,
        "semanticscholar.publication": SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    }

    for case in payload["publication_taxonomy_policy"].values():
        profile = profiles[case["profile"]]
        raw_rule = profile.rule_for(case["raw_field"])
        unified_rule = profile.rule_for(case["unified_field"])
        subclass_rule = profile.rule_for(case["subclass_field"])
        class_rule = profile.rule_for(case["class_field"])

        assert raw_rule is not None
        assert unified_rule is not None
        assert subclass_rule is not None
        assert class_rule is not None

        raw_value = raw_rule.apply(case["raw_input"])
        provider, _entity = case["profile"].split(".", maxsplit=1)
        entry = classify_publication_type(provider, raw_type=raw_value)

        if case["unified_expected"] is None:
            assert entry is None
            assert unified_rule.apply(case["unified_expected"]) is None
            assert subclass_rule.apply(case["subclass_expected"]) is None
            assert class_rule.apply(case["class_expected"]) is None
            continue

        assert entry is not None
        assert entry.unified_type == case["unified_expected"]
        assert entry.subclass == case["subclass_expected"]
        assert entry.class_code == case["class_expected"]
        assert unified_rule.apply(case["unified_expected"]) == case["unified_expected"]
        assert (
            subclass_rule.apply(case["subclass_expected"]) == case["subclass_expected"]
        )
        assert class_rule.apply(case["class_expected"]) == case["class_expected"]
