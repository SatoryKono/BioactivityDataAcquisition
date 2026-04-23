"""Integration tests for JSON hash stability."""

from __future__ import annotations


from bioetl.domain.normalization.profiles.chembl_assay import CHEMBL_ASSAY_PROFILE
from bioetl.domain.normalization.json import (
    deserialize_json_value,
    serialize_json_canonical,
)


class TestJsonHashStability:
    """Test that canonical JSON ensures stable content hashing."""

    def test_json_field_normalization_consistency(self) -> None:
        """Test that JSON fields are normalized consistently."""
        # Get the assay profile's JSON field rules
        json_fields = []
        for field_name, rule in CHEMBL_ASSAY_PROFILE.field_rules.items():
            if "JSON" in rule.notes:
                json_fields.append(field_name)

        assert len(json_fields) > 0, "Should have JSON fields"
        print(f"JSON fields in assay profile: {json_fields}")

        # Test that each JSON field uses the canonical normalizer
        for field_name in json_fields:
            rule = CHEMBL_ASSAY_PROFILE.field_rules[field_name]
            assert rule.normalizer.__name__ == "normalize_profile_json_string_strict"

    def test_hash_stability_with_different_key_orders(self) -> None:
        """Test that different JSON key orders produce same normalized result."""
        # All should normalize to the same result
        norm1 = serialize_json_canonical(
            {"year": 2023, "assay_type": "B", "confidence": 9}
        )
        norm2 = serialize_json_canonical(
            {"confidence": 9, "assay_type": "B", "year": 2023}
        )
        norm3 = serialize_json_canonical(
            {"assay_type": "B", "year": 2023, "confidence": 9}
        )

        assert norm1 == norm2 == norm3
        assert hash(norm1) == hash(norm2) == hash(norm3)

    def test_real_assay_json_examples(self) -> None:
        """Test with realistic assay JSON examples."""
        # Example assay_classifications JSON
        classifications1 = '{"type": "B", "category": "screening"}'
        classifications2 = '{"category": "screening", "type": "B"}'

        # Normalize through the profile
        rule = CHEMBL_ASSAY_PROFILE.field_rules["assay_classifications"]
        result1 = rule.normalizer(classifications1)
        result2 = rule.normalizer(classifications2)

        # Should produce identical results
        assert result1 == result2
        assert hash(result1) == hash(result2)

        # Verify the result is properly formatted
        assert '"category"' in result1
        assert '"type"' in result1

    def test_json_normalization_preserves_semantic_differences(self) -> None:
        """Test that semantically different JSON produces different results."""
        json1 = '{"assay_type": "B"}'
        json2 = '{"assay_type": "F"}'

        rule = CHEMBL_ASSAY_PROFILE.field_rules["assay_classifications"]
        result1 = rule.normalizer(json1)
        result2 = rule.normalizer(json2)

        # Should be different (semantic difference)
        assert result1 != result2
        assert hash(result1) != hash(result2)

    def test_invalid_json_collapses_to_none_for_strict_chembl_fields(self) -> None:
        """Strict ChEMBL JSON fields must fail closed on malformed payloads."""
        invalid_json = "not a valid json string"

        rule = CHEMBL_ASSAY_PROFILE.field_rules["assay_classifications"]
        result = rule.normalizer(invalid_json)

        assert result is None


class TestCrossPipelineJsonConsistency:
    """Test JSON normalization consistency across pipelines."""

    def test_json_normalization_unified(self) -> None:
        """Test that all pipelines use the same JSON normalization."""
        from bioetl.domain.normalization.profiles.chembl_activity import (
            CHEMBL_ACTIVITY_PROFILE,
        )
        from bioetl.domain.normalization.profiles.chembl_cell_line import (
            CHEMBL_CELL_LINE_PROFILE,
        )
        from bioetl.domain.normalization.profiles.chembl_tissue import (
            CHEMBL_TISSUE_PROFILE,
        )

        # Check that all profiles use the same JSON normalizer
        profiles = [
            CHEMBL_ACTIVITY_PROFILE,
            CHEMBL_ASSAY_PROFILE,
            CHEMBL_CELL_LINE_PROFILE,
            CHEMBL_TISSUE_PROFILE,
        ]

        for profile in profiles:
            for _field_name, rule in profile.field_rules.items():
                if "JSON" in rule.notes:
                    # Test with sample data
                    test_json = '{"key": "value"}'
                    result = rule.normalizer(test_json)
                    expected = '{"key":"value"}'
                    assert result == expected

    def test_unicode_and_special_characters(self) -> None:
        """Test JSON normalization with Unicode and special characters."""
        data = {
            "text": "Hello World",
            "special": "line1\nline2",
            "quote": 'He said "hello"',
            "numeric": 42,
        }

        result = serialize_json_canonical(data)

        # Should be valid JSON with proper escaping
        parsed = deserialize_json_value(result)
        assert parsed == data

    def test_numeric_precision(self) -> None:
        """Test that numeric precision is preserved in JSON."""
        data = {"float": 3.141592653589793, "large": 1e20, "small": 1e-20, "zero": 0.0}

        result = serialize_json_canonical(data)
        parsed = deserialize_json_value(result)

        # Numeric values should be preserved
        assert parsed["float"] == data["float"]
        assert parsed["large"] == data["large"]
        assert parsed["small"] == data["small"]
        assert parsed["zero"] == data["zero"]
