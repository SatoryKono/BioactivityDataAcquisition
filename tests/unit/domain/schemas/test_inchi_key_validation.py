"""Tests for InChI Key regex validation across Pandera schemas.

Tests INCHI_KEY_REGEX_PATTERN constant and schema InChI Key field validation.
Per IUPAC InChI specification: https://www.inchi-trust.org/

Requirements:
- First block MUST be 14 uppercase letters (connectivity layer)
- Second block MUST be 10 uppercase letters (stereochemistry + isotopes)
- Third block MUST be 1 uppercase letter (protonation)
- Total length MUST be 27 characters (14-10-1 with 2 hyphens)
"""

from __future__ import annotations

import re

import pytest

from bioetl.domain.validation import INCHI_KEY_REGEX_PATTERN


pytestmark = pytest.mark.unit

class TestInchiKeyRegexPattern:
    """Tests for INCHI_KEY_REGEX_PATTERN constant."""

    @pytest.mark.parametrize(
        "inchi_key,is_valid",
        [
            # Valid InChI Keys - real chemical compounds
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA-N", True),  # Aspirin
            ("RYYVLZVUVIJVGH-UHFFFAOYSA-N", True),  # Caffeine
            ("HEFNNWSXXWATRW-UHFFFAOYSA-N", True),  # Paracetamol
            ("RZVAJINKPMORJF-UHFFFAOYSA-N", True),  # Ibuprofen
            ("XLYOFNOQVPJJNP-UHFFFAOYSA-N", True),  # Water
            ("OKKJLVBELUTLKV-UHFFFAOYSA-N", True),  # Methanol
            # Valid InChI Keys - format check (all uppercase letters)
            ("XXXXXXXXXXXXXX-YYYYYYYYYY-Z", True),
            ("ABCDEFGHIJKLMN-OPQRSTUVWX-Y", True),
            ("AAAAAAAAAAAAAA-BBBBBBBBBB-C", True),
            ("ZZZZZZZZZZZZZZ-ZZZZZZZZZZ-Z", True),
            # Invalid InChI Keys - lowercase
            ("bsynrymutxbxsq-uhfffaoysa-n", False),
            ("BSYNRYMUTXBXSQ-uhfffaoysa-N", False),
            ("bsynrymutxbxsq-UHFFFAOYSA-N", False),
            # Invalid InChI Keys - wrong first block length
            ("BSYNRYMUTXBXS-UHFFFAOYSA-N", False),  # 13 chars (too short)
            ("BSYNRYMUTXBXSQA-UHFFFAOYSA-N", False),  # 15 chars (too long)
            ("BSYNRYMUTXB-UHFFFAOYSA-N", False),  # 11 chars (too short)
            # Invalid InChI Keys - wrong second block length
            ("BSYNRYMUTXBXSQ-UHFFFAOYS-N", False),  # 9 chars (too short)
            ("BSYNRYMUTXBXSQ-UHFFFAOYSAA-N", False),  # 11 chars (too long)
            ("BSYNRYMUTXBXSQ-UHFFFFF-N", False),  # 7 chars (too short)
            # Invalid InChI Keys - wrong third block length
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA-", False),  # 0 chars (empty)
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA-NN", False),  # 2 chars (too long)
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA-NNN", False),  # 3 chars (too long)
            # Invalid InChI Keys - wrong separator
            ("BSYNRYMUTXBXSQ_UHFFFAOYSA_N", False),
            ("BSYNRYMUTXBXSQ.UHFFFAOYSA.N", False),
            ("BSYNRYMUTXBXSQ UHFFFAOYSA N", False),
            # Invalid InChI Keys - no separators
            ("BSYNRYMUTXBXSQUHFFFAOYSAN", False),
            # Invalid InChI Keys - numbers or special characters
            ("123456789012345-1234567890-X", False),
            ("BSYNRYMUTXBXS1-UHFFFAOYSA-N", False),
            ("BSYNRYMUTXBXSQ-UHFFFAOYS1-N", False),
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA-1", False),
            # Invalid InChI Keys - malformed
            ("", False),
            ("BSYNRYMUTXBXSQ", False),
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA", False),
            ("-UHFFFAOYSA-N", False),
            ("BSYNRYMUTXBXSQ--N", False),
        ],
    )
    def test_inchi_key_regex_validation(self, inchi_key: str, is_valid: bool) -> None:
        """Test InChI Key regex pattern matches IUPAC specification.

        Validates that:
        - First block has exactly 14 uppercase letters
        - Second block has exactly 10 uppercase letters
        - Third block has exactly 1 uppercase letter
        - Blocks are separated by hyphens
        """
        result = bool(re.match(INCHI_KEY_REGEX_PATTERN, inchi_key))
        assert result == is_valid, (
            f"InChI Key '{inchi_key}' should be {'valid' if is_valid else 'invalid'}"
        )

    def test_key_regex_pattern__pattern_is_string__28402674(self) -> None:
        """Test INCHI_KEY_REGEX_PATTERN is exported as string for Pandera str_matches."""
        assert isinstance(INCHI_KEY_REGEX_PATTERN, str)
        assert INCHI_KEY_REGEX_PATTERN.startswith("^")
        assert INCHI_KEY_REGEX_PATTERN.endswith("$")

    def test_key_regex_pattern__pattern_components__9e6037f3(self) -> None:
        """Test InChI Key regex pattern has correct components."""
        # Pattern should be: ^[A-Z]{14}-[A-Z]{10}-[A-Z]$
        assert "[A-Z]{14}" in INCHI_KEY_REGEX_PATTERN, (
            "Pattern should require 14 uppercase letters in first block"
        )
        assert "[A-Z]{10}" in INCHI_KEY_REGEX_PATTERN, (
            "Pattern should require 10 uppercase letters in second block"
        )
        assert "-" in INCHI_KEY_REGEX_PATTERN, "Pattern should have hyphen separators"


class TestInchiKeyRegexEdgeCases:
    """Edge case tests for InChI Key validation."""

    @pytest.mark.parametrize(
        "first_block_length",
        [1, 5, 10, 13, 15, 20],
    )
    def test_wrong_first_block_length_rejected(self, first_block_length: int) -> None:
        """Test that first blocks with != 14 letters are rejected."""
        first_block = "A" * first_block_length
        inchi_key = f"{first_block}-UHFFFAOYSA-N"
        assert not re.match(INCHI_KEY_REGEX_PATTERN, inchi_key)

    def test_correct_first_block_length_accepted(self) -> None:
        """Test that first block with exactly 14 letters is accepted."""
        first_block = "A" * 14
        inchi_key = f"{first_block}-UHFFFAOYSA-N"
        assert re.match(INCHI_KEY_REGEX_PATTERN, inchi_key)

    @pytest.mark.parametrize(
        "second_block_length",
        [1, 5, 9, 11, 15],
    )
    def test_wrong_second_block_length_rejected(self, second_block_length: int) -> None:
        """Test that second blocks with != 10 letters are rejected."""
        second_block = "B" * second_block_length
        inchi_key = f"BSYNRYMUTXBXSQ-{second_block}-N"
        assert not re.match(INCHI_KEY_REGEX_PATTERN, inchi_key)

    def test_correct_second_block_length_accepted(self) -> None:
        """Test that second block with exactly 10 letters is accepted."""
        second_block = "B" * 10
        inchi_key = f"BSYNRYMUTXBXSQ-{second_block}-N"
        assert re.match(INCHI_KEY_REGEX_PATTERN, inchi_key)

    @pytest.mark.parametrize(
        "third_block_length",
        [0, 2, 3, 5],
    )
    def test_wrong_third_block_length_rejected(self, third_block_length: int) -> None:
        """Test that third blocks with != 1 letter are rejected."""
        third_block = "C" * third_block_length if third_block_length > 0 else ""
        inchi_key = f"BSYNRYMUTXBXSQ-UHFFFAOYSA-{third_block}"
        assert not re.match(INCHI_KEY_REGEX_PATTERN, inchi_key)

    def test_correct_third_block_length_accepted(self) -> None:
        """Test that third block with exactly 1 letter is accepted."""
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            inchi_key = f"BSYNRYMUTXBXSQ-UHFFFAOYSA-{letter}"
            assert re.match(INCHI_KEY_REGEX_PATTERN, inchi_key)


class TestInchiKeySchemaIntegration:
    """Integration tests verifying INCHI_KEY_REGEX_PATTERN is used in schemas."""

    def test_chembl_molecule_uses_inchi_key_regex_pattern(self) -> None:
        """Test ChEMBL MoleculeSchema uses INCHI_KEY_REGEX_PATTERN constant."""
        from bioetl.domain.schemas.chembl import molecule

        # Verify the import exists
        assert hasattr(molecule, "INCHI_KEY_REGEX_PATTERN")
        assert molecule.INCHI_KEY_REGEX_PATTERN == INCHI_KEY_REGEX_PATTERN

    def test_pubchem_molecule_uses_inchi_key_regex_pattern(self) -> None:
        """Test PubChem PubchemMoleculeSchema uses INCHI_KEY_REGEX_PATTERN constant."""
        from bioetl.domain.schemas.pubchem import compound

        # Verify the import exists
        assert hasattr(compound, "INCHI_KEY_REGEX_PATTERN")
        assert compound.INCHI_KEY_REGEX_PATTERN == INCHI_KEY_REGEX_PATTERN

    def test_key_schema_schemas_inchi_key_validation_178__e6c79636(
        self,
    ) -> None:
        """Test all molecule schemas use the same InChI Key pattern value."""
        from bioetl.domain.schemas.chembl import molecule as chembl_mol
        from bioetl.domain.schemas.pubchem import compound as pubchem_mol

        patterns = [
            chembl_mol.INCHI_KEY_REGEX_PATTERN,
            pubchem_mol.INCHI_KEY_REGEX_PATTERN,
        ]

        # All patterns should be identical
        assert all(p == INCHI_KEY_REGEX_PATTERN for p in patterns)
