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
"""Unit tests for UniProt CommentExtractor."""

import json

import pytest

from bioetl.application.pipelines.uniprot.extractors.comments import (
    CommentExtractor,
    _is_comment_of_type,
    _extract_texts_from_dict,
)


pytestmark = pytest.mark.unit


class TestCommentExtractor:
    """Tests for CommentExtractor class."""

    def test_comment_extractor__function_comment__3465819d(self):
        """Test extraction of FUNCTION comments."""
        comments = [
            {"commentType": "FUNCTION", "texts": [{"value": "Acts as a enzyme."}]}
        ]
        result = CommentExtractor.extract_by_type(comments, "FUNCTION")
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0] == "Acts as a enzyme."

    def test_comment_extractor__catalytic_activity__db6e436b(self):
        """Test extraction of CATALYTIC ACTIVITY."""
        comments = [
            {
                "commentType": "CATALYTIC ACTIVITY",
                "reaction": {"name": "ATP + H2O = ADP + P", "ecNumber": "3.6.1.3"},
            }
        ]
        result = CommentExtractor.extract_catalytic_activity(comments)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["reaction"] == "ATP + H2O = ADP + P"
        assert parsed[0]["ec_number"] == "3.6.1.3"

    def test_extract_subcellular_locations(self):
        """Test extraction of SUBCELLULAR LOCATION."""
        comments = [
            {
                "commentType": "SUBCELLULAR LOCATION",
                "subcellularLocations": [
                    {"location": {"value": "Cytoplasm"}},
                    {"location": {"value": "Nucleus"}},
                ],
            }
        ]
        result = CommentExtractor.extract_subcellular_locations(comments)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert "Cytoplasm" in parsed
        assert "Nucleus" in parsed

    def test_comment_extractor__alternative_products__f1e7521c(self):
        """Test extraction of ALTERNATIVE PRODUCTS."""
        comments = [
            {
                "commentType": "ALTERNATIVE PRODUCTS",
                "isoforms": [
                    {"name": {"value": "Isoform 1"}, "isoformIds": ["P12345-1"]}
                ],
            }
        ]
        result = CommentExtractor.extract_alternative_products(comments)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "Isoform 1"
        assert parsed[0]["ids"] == ["P12345-1"]

    def test_count_isoforms(self):
        """Test counting isoforms."""
        comments = [
            {
                "commentType": "ALTERNATIVE PRODUCTS",
                "isoforms": [
                    {"name": {"value": "Isoform 1"}},
                    {"name": {"value": "Isoform 2"}},
                ],
            }
        ]
        count = CommentExtractor.count_isoforms(comments)
        assert count == 2

    def test_extract_cofactors(self):
        """Test extraction of COFACTOR comments."""
        comments = [
            {
                "commentType": "COFACTOR",
                "cofactors": [
                    {
                        "name": "Mg(2+)",
                        "cofactorCrossReference": {"id": "CHEBI:18420"},
                        "note": {"texts": [{"value": "Bind 1 magnesium ion."}]},
                    }
                ],
            }
        ]
        result = CommentExtractor.extract_cofactors(comments)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "Mg(2+)"
        assert parsed[0]["chebi_id"] == "CHEBI:18420"
        assert parsed[0]["note"] == "Bind 1 magnesium ion."

    def test_extract_biophysicochemical_properties(self):
        """Test extraction of BIOPHYSICOCHEMICAL PROPERTIES."""
        comments = [
            {
                "commentType": "BIOPHYSICOCHEMICAL PROPERTIES",
                "phDependence": {"texts": [{"value": "Optimum pH is 7."}]},
                "kineticParameters": {
                    "michaelisConstants": [
                        {"constant": 1.5, "unit": "mM", "substrate": "ATP"}
                    ]
                },
            }
        ]
        result = CommentExtractor.extract_biophysicochemical_properties(comments)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["ph_dependence"] == ["Optimum pH is 7."]
        assert parsed["kinetic_parameters"]["km"][0]["value"] == pytest.approx(1.5)

    def test_comment_extractor__extract_induction__abeb5687(self):
        """Test extraction of INDUCTION comments."""
        comments = [
            {"commentType": "INDUCTION", "texts": [{"value": "Induced by stress."}]}
        ]
        result = CommentExtractor.extract_induction(comments)
        assert result is not None
        parsed = json.loads(result)
        assert parsed[0] == "Induced by stress."

    def test_extract_isoform_details(self):
        """Test extraction of detailed isoform info."""
        comments = [
            {
                "commentType": "ALTERNATIVE PRODUCTS",
                "isoforms": [
                    {
                        "name": {"value": "Isoform A"},
                        "isoformIds": ["P12345-1"],
                        "synonyms": [{"value": "Variant 1"}],
                    }
                ],
            }
        ]
        result = CommentExtractor.extract_isoform_details(comments)
        assert result["isoform_names"] is not None
        assert result["isoform_ids"] is not None
        assert result["isoform_synonyms"] is not None

        assert "Isoform A" in json.loads(result["isoform_names"])
        assert "P12345-1" in json.loads(result["isoform_ids"])
        assert "Variant 1" in json.loads(result["isoform_synonyms"])

    def test_extract_reactions(self):
        """Test extraction of reaction names."""
        comments = [
            {"commentType": "CATALYTIC ACTIVITY", "reaction": {"name": "Reaction A"}}
        ]
        result = CommentExtractor.extract_reactions(comments)
        assert result is not None
        assert "Reaction A" in json.loads(result)

    def test_extract_reaction_ec_numbers(self):
        """Test extraction of reaction EC numbers."""
        comments = [
            {"commentType": "CATALYTIC ACTIVITY", "reaction": {"ecNumber": "1.1.1.1"}}
        ]
        result = CommentExtractor.extract_reaction_ec_numbers(comments)
        assert result is not None
        assert "1.1.1.1" in json.loads(result)

    def test_helper_is_comment_of_type(self):
        """Test _is_comment_of_type helper."""
        assert _is_comment_of_type({"commentType": "TEST"}, "TEST") is True
        assert _is_comment_of_type({"commentType": "OTHER"}, "TEST") is False
        assert _is_comment_of_type("not a dict", "TEST") is False

    def test_helper_extract_texts_from_dict(self):
        """Test _extract_texts_from_dict helper."""
        data = {"texts": [{"value": "Text 1"}, {"value": "Text 2"}]}
        assert _extract_texts_from_dict(data) == ["Text 1", "Text 2"]
        assert _extract_texts_from_dict({}) == []
        assert _extract_texts_from_dict(None) == []
        assert _extract_texts_from_dict({"texts": "not list"}) == []

    def test_extract_by_type_none(self):
        """Test extract_by_type with empty input."""
        assert CommentExtractor.extract_by_type(None, "TYPE") is None
        assert CommentExtractor.extract_by_type([], "TYPE") is None

    def test_extract_text_values_direct(self):
        """Test direct text extraction helper method."""
        comments = [
            {"commentType": "FUNCTION", "texts": [{"value": "Function A"}]},
            {"commentType": "FUNCTION", "texts": [{"value": "Function B"}]},
            {"commentType": "PATHWAY", "texts": [{"value": "Pathway A"}]},
        ]
        result = CommentExtractor.extract_text_values(comments, "FUNCTION")
        assert result == ["Function A", "Function B"]

    def test_extract_catalytic_activity_ignores_invalid_reaction(self):
        """Invalid reaction payload should not crash and should return None."""
        comments = [{"commentType": "CATALYTIC ACTIVITY", "reaction": "invalid"}]
        assert CommentExtractor.extract_catalytic_activity(comments) is None

    def test_extract_isoform_details_returns_none_for_empty_payload(self):
        """Isoform detail fields must remain None when no isoforms are present."""
        result = CommentExtractor.extract_isoform_details(None)
        assert result == {
            "isoform_names": None,
            "isoform_ids": None,
            "isoform_synonyms": None,
        }

    def test_extract_all_comments_raw(self):
        """Test aggregated raw extraction output."""
        comments = [
            {"commentType": "FUNCTION", "texts": [{"value": "Kinase activity"}]},
            {
                "commentType": "CATALYTIC ACTIVITY",
                "reaction": {"name": "ATP + H2O = ADP + P", "ecNumber": "3.6.1.3"},
            },
            {
                "commentType": "ALTERNATIVE PRODUCTS",
                "isoforms": [
                    {
                        "name": {"value": "Isoform A"},
                        "isoformIds": ["P12345-1"],
                        "synonyms": [{"value": "Variant 1"}],
                    }
                ],
            },
        ]
        raw = CommentExtractor.extract_all_comments_raw(comments)

        assert raw["function_comment"] == ["Kinase activity"]
        assert raw["isoform_count"] == 1
        assert isinstance(raw["catalytic_activity"], list)
        assert isinstance(raw["reactions"], list)
        assert isinstance(raw["reaction_ec_numbers"], list)

    def test_extract_all_comments(self):
        """Test aggregated serialized extraction output."""
        comments = [
            {"commentType": "FUNCTION", "texts": [{"value": "Kinase activity"}]},
            {
                "commentType": "CATALYTIC ACTIVITY",
                "reaction": {"name": "ATP + H2O = ADP + P", "ecNumber": "3.6.1.3"},
            },
        ]
        result = CommentExtractor.extract_all_comments(comments)

        assert result["function_comment"] == '["Kinase activity"]'
        assert result["catalytic_activity"] is not None
        assert result["reactions"] is not None
        assert result["reaction_ec_numbers"] is not None
        assert result["isoform_count"] is None
