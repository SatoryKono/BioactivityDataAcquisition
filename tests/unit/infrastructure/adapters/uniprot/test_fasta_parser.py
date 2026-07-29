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
"""Unit tests for FastaParser.

Tests cover: parse(), parse_header(), edge cases and error paths.
"""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.uniprot.fasta_parser import FastaParser


@pytest.mark.unit
class TestFastaParserParse:
    """Tests for FastaParser.parse()."""

    def test_parse_empty_string_returns_empty_list(self) -> None:
        """Empty FASTA text returns empty list."""
        result = FastaParser.parse("")
        assert result == []

    def test_parse_single_record(self) -> None:
        """Single FASTA record is parsed correctly."""
        fasta = ">sp|P12345|GENE_HUMAN Description\nMKTAYIAKQR\n"
        result = FastaParser.parse(fasta)
        assert len(result) == 1
        assert result[0]["header"] == "sp|P12345|GENE_HUMAN Description"
        assert result[0]["sequence"] == "MKTAYIAKQR"

    def test_parse_multiple_records(self) -> None:
        """Multiple FASTA records are all parsed."""
        fasta = (
            ">sp|P12345|GENE1_HUMAN First\nMKTAYIAKQR\n"
            ">sp|Q67890|GENE2_MOUSE Second\nACDEFGHIKL\n"
        )
        result = FastaParser.parse(fasta)
        assert len(result) == 2
        assert result[0]["header"] == "sp|P12345|GENE1_HUMAN First"
        assert result[1]["header"] == "sp|Q67890|GENE2_MOUSE Second"

    def test_parse_multiline_sequence(self) -> None:
        """Sequences spanning multiple lines are concatenated."""
        fasta = ">sp|P12345|GENE_HUMAN\nMKTAY\nIAKQR\nLMNPQ\n"
        result = FastaParser.parse(fasta)
        assert len(result) == 1
        assert result[0]["sequence"] == "MKTAYIAKQRLMNPQ"

    def test_parse_ignores_blank_lines(self) -> None:
        """Blank lines within sequence are ignored."""
        fasta = ">sp|P12345|GENE\nMKTAY\n\nIAKQR\n"
        result = FastaParser.parse(fasta)
        assert result[0]["sequence"] == "MKTAYIAKQR"

    def test_parse_strips_whitespace_from_lines(self) -> None:
        """Whitespace is stripped from each line."""
        fasta = ">sp|P12345|GENE_HUMAN  \n  MKTAY  \n"
        result = FastaParser.parse(fasta)
        assert result[0]["header"] == "sp|P12345|GENE_HUMAN"
        assert result[0]["sequence"] == "MKTAY"

    def test_parse_no_sequence_data(self) -> None:
        """Record with no sequence data yields empty string."""
        fasta = ">sp|P12345|GENE_HUMAN\n"
        result = FastaParser.parse(fasta)
        assert len(result) == 1
        assert result[0]["sequence"] == ""

    def test_parse_only_whitespace_lines(self) -> None:
        """Text with only whitespace lines returns empty list."""
        result = FastaParser.parse("   \n   \n")
        assert result == []

    def test_parse_header_without_gt_prefix(self) -> None:
        """Lines not starting with > are treated as sequence lines."""
        fasta = ">GENE1\nABC\nDEF\n"
        result = FastaParser.parse(fasta)
        assert result[0]["sequence"] == "ABCDEF"

    def test_parse_preserves_last_record(self) -> None:
        """Last record without trailing newline is included."""
        fasta = ">GENE1\nMKTAY\n>GENE2\nACDEF"
        result = FastaParser.parse(fasta)
        assert len(result) == 2
        assert result[1]["sequence"] == "ACDEF"

    def test_parse_returns_list_of_dicts(self) -> None:
        """Result is a list of dicts with required keys."""
        fasta = ">sp|P12345|GENE\nMKTAY\n"
        result = FastaParser.parse(fasta)
        assert isinstance(result, list)
        assert "header" in result[0]
        assert "sequence" in result[0]


@pytest.mark.unit
class TestFastaParserParseHeader:
    """Tests for FastaParser.parse_header()."""

    def test_parse_uniprot_format(self) -> None:
        """Standard UniProt format is parsed into components."""
        header = "sp|P12345|GENE_HUMAN Some Description Here"
        result = FastaParser.parse_header(header)
        assert result["database"] == "sp"
        assert result["accession"] == "P12345"
        assert result["entry_name"] == "GENE_HUMAN"
        assert result["description"] == "Some Description Here"

    def test_parse_uniprot_format_no_description(self) -> None:
        """UniProt format without description part."""
        header = "sp|P12345|GENE_HUMAN"
        result = FastaParser.parse_header(header)
        assert result["database"] == "sp"
        assert result["accession"] == "P12345"
        assert result["entry_name"] == "GENE_HUMAN"
        assert result["description"] is None

    def test_parse_trembl_database(self) -> None:
        """TrEMBL (tr) database prefix is correctly parsed."""
        header = "tr|A0A000|GENEX_MOUSE Mouse protein"
        result = FastaParser.parse_header(header)
        assert result["database"] == "tr"
        assert result["accession"] == "A0A000"

    def test_parse_simple_format_no_pipes(self) -> None:
        """Simple header without pipes is treated as description only."""
        header = "Just a simple description"
        result = FastaParser.parse_header(header)
        assert result["database"] is None
        assert result["accession"] is None
        assert result["entry_name"] is None
        assert result["description"] == "Just a simple description"

    def test_parse_two_pipe_parts_fallback(self) -> None:
        """Header with only 2 pipe-parts falls through to simple format."""
        header = "db|accession"
        result = FastaParser.parse_header(header)
        # Only 2 parts, len < 3 → simple format
        assert result["database"] is None
        assert result["description"] == "db|accession"

    def test_parse_empty_header(self) -> None:
        """Empty header returns all None values in simple format."""
        result = FastaParser.parse_header("")
        assert result["database"] is None
        assert result["description"] == ""

    @pytest.mark.parametrize(
        "header,expected_accession",
        [
            ("sp|P00533|EGFR_HUMAN Epidermal growth factor receptor", "P00533"),
            (
                "sp|Q9UBS4|EIF2B5_HUMAN Translation initiation factor eIF2B subunit epsilon",
                "Q9UBS4",
            ),
            ("tr|A0A087WZD4|A0A087WZD4_HUMAN Uncharacterized protein", "A0A087WZD4"),
        ],
    )
    def test_parse_various_accessions(
        self, header: str, expected_accession: str
    ) -> None:
        """Various real UniProt accession formats are parsed correctly."""
        result = FastaParser.parse_header(header)
        assert result["accession"] == expected_accession


@pytest.mark.unit
class TestFastaParserIntegration:
    """Integration tests: parse() then parse_header() on each record."""

    def test_parse_and_parse_header_pipeline(self) -> None:
        """Full pipeline: parse text then parse each header."""
        fasta = (
            ">sp|P00533|EGFR_HUMAN Epidermal growth factor receptor\n"
            "MRPSGTAGAALLALLAALCPASRA\n"
            ">tr|A0A000|PROT_MOUSE Mouse protein\n"
            "ACDEFGHIKLM\n"
        )
        records = FastaParser.parse(fasta)
        assert len(records) == 2

        hdr1 = FastaParser.parse_header(records[0]["header"])
        assert hdr1["accession"] == "P00533"
        assert hdr1["entry_name"] == "EGFR_HUMAN"

        hdr2 = FastaParser.parse_header(records[1]["header"])
        assert hdr2["database"] == "tr"
        assert hdr2["accession"] == "A0A000"
