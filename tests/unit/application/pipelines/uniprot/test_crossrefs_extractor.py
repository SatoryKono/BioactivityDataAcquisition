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
"""Unit tests for UniProt CrossRefExtractor."""

import pytest

import json
from bioetl.application.pipelines.uniprot.extractors.crossrefs import CrossRefExtractor


pytestmark = pytest.mark.unit


class TestCrossRefExtractor:
    """Tests for CrossRefExtractor class."""

    def test_cross_ref_extractor__extract_go_terms__b116c64b(self):
        """Test extraction of GO terms."""
        xrefs = [
            {
                "database": "GO",
                "id": "GO:0005524",
                "properties": [
                    {"key": "GoTerm", "value": "F:ATP binding"},
                    {"key": "GoEvidenceType", "value": "IDA:PubMed"},
                ],
            }
        ]
        result = CrossRefExtractor.extract_go_terms(xrefs)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "GO:0005524"
        assert parsed[0]["term"] == "ATP binding"
        assert parsed[0]["aspect"] == "F"
        assert parsed[0]["evidence"] == "IDA:PubMed"

    def test_extract_xref_ids(self):
        """Test extraction of simple xref IDs."""
        xrefs = [
            {"database": "DrugBank", "id": "DB00001"},
            {"database": "PDB", "id": "1ABC"},
        ]
        result = CrossRefExtractor.extract_xref_ids(xrefs, "DrugBank")
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0] == "DB00001"

    def test_cross_ref_extractor__extract_pdb_xrefs__0c8ea5a8(self):
        """Test extraction of PDB xrefs."""
        xrefs = [
            {
                "database": "PDB",
                "id": "1ABC",
                "properties": [
                    {"key": "Method", "value": "X-ray"},
                    {"key": "Resolution", "value": "1.50 A"},
                    {"key": "Chains", "value": "A=1-100"},
                ],
            }
        ]
        result = CrossRefExtractor.extract_pdb_xrefs(xrefs)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "1ABC"
        assert parsed[0]["method"] == "X-ray"
        assert parsed[0]["resolution"] == "1.50 A"
        assert parsed[0]["chains"] == "A=1-100"

    def test_extract_interpro_xrefs(self):
        """Test extraction of InterPro xrefs."""
        xrefs = [
            {
                "database": "InterPro",
                "id": "IPR000001",
                "properties": [{"key": "EntryName", "value": "Kringle"}],
            }
        ]
        result = CrossRefExtractor.extract_interpro_xrefs(xrefs)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "IPR000001"
        assert parsed[0]["name"] == "Kringle"

    def test_extract_pfam_xrefs(self):
        """Test extraction of Pfam xrefs."""
        xrefs = [
            {
                "database": "Pfam",
                "id": "PF00001",
                "properties": [
                    {"key": "EntryName", "value": "7tm_1"},
                    {"key": "MatchStatus", "value": "1"},
                ],
            }
        ]
        result = CrossRefExtractor.extract_pfam_xrefs(xrefs)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "PF00001"
        assert parsed[0]["name"] == "7tm_1"
        assert parsed[0]["match_status"] == "1"

    def test_extract_reactome_xrefs(self):
        """Test extraction of Reactome xrefs."""
        xrefs = [
            {
                "database": "Reactome",
                "id": "R-HSA-164843",
                "properties": [
                    {"key": "PathwayName", "value": "2-LTR circle formation"}
                ],
            }
        ]
        result = CrossRefExtractor.extract_reactome_xrefs(xrefs)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "R-HSA-164843"
        assert parsed[0]["pathway_name"] == "2-LTR circle formation"

    def test_extract_molecular_function(self):
        """Test extraction of Molecular Function GO terms."""
        xrefs = [
            {
                "database": "GO",
                "id": "GO:0005524",
                "properties": [{"key": "GoTerm", "value": "F:ATP binding"}],
            },
            {
                "database": "GO",
                "id": "GO:0005634",
                "properties": [{"key": "GoTerm", "value": "C:nucleus"}],
            },
        ]
        result = CrossRefExtractor.extract_molecular_function(xrefs)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["term"] == "ATP binding"

    def test_extract_cellular_component(self):
        """Test extraction of Cellular Component GO terms."""
        xrefs = [
            {
                "database": "GO",
                "id": "GO:0005524",
                "properties": [{"key": "GoTerm", "value": "F:ATP binding"}],
            },
            {
                "database": "GO",
                "id": "GO:0005634",
                "properties": [{"key": "GoTerm", "value": "C:nucleus"}],
            },
        ]
        result = CrossRefExtractor.extract_cellular_component(xrefs)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["term"] == "nucleus"

    def test_helper_parse_properties(self):
        """Test _parse_properties helper."""
        props = [
            {"key": "Key1", "value": "Val1"},
            {"key": "Key2", "value": "Val2"},
            "invalid",
            {},
        ]
        result = CrossRefExtractor._parse_properties(props)
        assert result == {"Key1": "Val1", "Key2": "Val2"}
        assert CrossRefExtractor._parse_properties(None) == {}

    def test_helper_parse_go_term_value(self):
        """Test _parse_go_term_value helper."""
        assert CrossRefExtractor._parse_go_term_value("F:Term") == ("F", "Term")
        assert CrossRefExtractor._parse_go_term_value("P:Term") == ("P", "Term")
        assert CrossRefExtractor._parse_go_term_value("C:Term") == ("C", "Term")
        assert CrossRefExtractor._parse_go_term_value("X:Term") == (None, "Term")
        assert CrossRefExtractor._parse_go_term_value("Invalid") == (None, None)
        assert CrossRefExtractor._parse_go_term_value(None) == (None, None)

    def test_extract_go_by_aspect_invalid(self):
        """Test extract_go_by_aspect with invalid aspect."""
        assert CrossRefExtractor.extract_go_by_aspect([], "X") is None
        assert CrossRefExtractor.extract_go_by_aspect(None, "F") is None

    def test_build_pdb_entry_missing_id(self):
        """_build_pdb_entry should return None when ID is missing."""
        assert CrossRefExtractor._build_pdb_entry({"database": "PDB"}) is None

    def test_build_interpro_entry_without_name(self):
        """_build_interpro_entry should keep ID when name is absent."""
        result = CrossRefExtractor._build_interpro_entry(
            {"database": "InterPro", "id": "IPR123", "properties": []}
        )
        assert result == {"id": "IPR123"}

    def test_build_pfam_entry_without_optional_fields(self):
        """_build_pfam_entry should emit only ID when optional props absent."""
        result = CrossRefExtractor._build_pfam_entry(
            {"database": "Pfam", "id": "PF001", "properties": []}
        )
        assert result == {"id": "PF001"}

    def test_build_reactome_entry_without_pathway_name(self):
        """_build_reactome_entry should emit only ID when name is absent."""
        result = CrossRefExtractor._build_reactome_entry(
            {"database": "Reactome", "id": "R-HSA-123", "properties": []}
        )
        assert result == {"id": "R-HSA-123"}

    def test_extract_xref_ids_ignores_invalid_entries(self):
        """extract_xref_ids should ignore malformed xref elements."""
        xrefs = [
            {"database": "DrugBank", "id": "DB001"},
            {"database": "DrugBank", "id": None},
            {"database": "PDB", "id": "1ABC"},
            "invalid",
            {"database": "DrugBank"},
        ]
        result = CrossRefExtractor.extract_xref_ids(xrefs, "DrugBank")
        assert result is not None
        assert json.loads(result) == ["DB001"]
