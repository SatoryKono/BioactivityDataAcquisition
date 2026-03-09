"""Unit tests for edge cases in domain transformations.

Tests Unicode input, malformed values, null handling and boundary conditions
for safe_float, safe_int, safe_str and normalize_for_hash.

These complement tests/unit/domain/transformations/test_coercion.py by adding
coverage for non-ASCII input, zero-width characters, surrogate code points and
multi-language strings.
"""

from __future__ import annotations

import pytest

from bioetl.domain.transformations.coercion import safe_float, safe_int, safe_str
from bioetl.domain.transformations.hashing import normalize_for_hash


# =============================================================================
# safe_float — Unicode and malformed input edge cases
# =============================================================================


@pytest.mark.unit
class TestSafeFloatEdgeCases:
    """Edge cases for safe_float beyond basic coercion tests."""

    # -- Unicode / non-ASCII --------------------------------------------------

    def test_arabic_indic_digit_string_behaviour(self) -> None:
        """Python's float() converts Arabic-Indic digits (Unicode Nd category).

        CPython's float() accepts any Unicode decimal digit character, so
        Arabic-Indic numerals like '٣.١٤' are parsed as 3.14.
        """
        # Verified: Python converts Arabic-Indic digits transparently
        assert safe_float("٣.١٤") == pytest.approx(3.14)

    def test_fullwidth_digit_string_behaviour(self) -> None:
        """Python's float() converts fullwidth Unicode digits.

        Fullwidth variants such as '３.１４' are treated as standard digits
        by CPython's numeric coercion and return 3.14.
        """
        # Verified: Python converts fullwidth Unicode digits transparently
        assert safe_float("３.１４") == pytest.approx(3.14)

    def test_superscript_digit_string_returns_default(self) -> None:
        """Superscript digit characters should return default."""
        assert safe_float("²") is None

    def test_zero_width_space_in_number_returns_default(self) -> None:
        """Zero-width space embedded in a numeric string should return default."""
        assert safe_float("3\u200b.14") is None  # ZWSP between digits

    def test_unicode_minus_sign_returns_default(self) -> None:
        """Unicode minus (U+2212) is not a valid float literal."""
        assert safe_float("\u22121.5") is None

    def test_mixed_latin_cyrillic_returns_default(self) -> None:
        """String with Cyrillic characters is not a valid number."""
        assert safe_float("3.1а4") is None  # Cyrillic 'а'

    # -- Malformed inputs -------------------------------------------------------

    def test_empty_string_returns_default(self) -> None:
        assert safe_float("") is None

    def test_whitespace_only_returns_default(self) -> None:
        assert safe_float("   ") is None

    def test_comma_decimal_separator_returns_default(self) -> None:
        """European decimal comma is not valid Python float literal."""
        assert safe_float("3,14") is None

    def test_hex_string_returns_default(self) -> None:
        assert safe_float("0xff") is None

    def test_exponential_notation_succeeds(self) -> None:
        """Scientific notation strings are valid float literals."""
        assert safe_float("1e3") == 1000.0

    def test_list_returns_default(self) -> None:
        assert safe_float([1.0, 2.0]) is None

    def test_dict_returns_default(self) -> None:
        assert safe_float({"value": 1.0}) is None

    # -- Null handling ----------------------------------------------------------

    def test_none_always_returns_none(self) -> None:
        assert safe_float(None) is None

    def test_none_with_zero_default(self) -> None:
        assert safe_float(None, default=0.0) == 0.0

    def test_false_returns_default(self) -> None:
        assert safe_float(False) is None

    def test_true_returns_default(self) -> None:
        assert safe_float(True) is None


# =============================================================================
# safe_int — Unicode and malformed input edge cases
# =============================================================================


@pytest.mark.unit
class TestSafeIntEdgeCases:
    """Edge cases for safe_int beyond basic coercion tests."""

    # -- Unicode / non-ASCII --------------------------------------------------

    def test_arabic_indic_digit_behaviour(self) -> None:
        """Python's int() parses Arabic-Indic digit characters (Unicode Nd category).

        CPython's int() accepts any Unicode decimal digit character, so
        Arabic-Indic numerals like '٤٢' are parsed as 42.
        """
        # Verified: Python parses Arabic-Indic integers transparently
        assert safe_int("٤٢") == 42

    def test_fullwidth_digit_behaviour(self) -> None:
        """Python's int() parses fullwidth digit characters.

        Fullwidth variants such as '４２' are treated as standard digits
        by CPython's int() and return 42.
        """
        # Verified: Python parses fullwidth Unicode integers transparently
        assert safe_int("４２") == 42

    def test_roman_numeral_returns_default(self) -> None:
        assert safe_int("XLII") is None

    def test_zero_width_nobreak_space_returns_default(self) -> None:
        assert safe_int("4\ufeff2") is None  # BOM / ZWNBSP

    # -- Malformed inputs -------------------------------------------------------

    def test_empty_string_returns_default(self) -> None:
        assert safe_int("") is None

    def test_decimal_string_without_fraction_returns_default(self) -> None:
        """'42.0' cannot be parsed by int() directly and returns None.

        safe_int routes string inputs through int(str(value).strip()), which
        raises ValueError for '42.0', so the default (None) is returned.
        Use safe_float() for decimal strings instead.
        """
        assert safe_int("42.0") is None

    def test_decimal_string_with_fraction_returns_default(self) -> None:
        """'42.9' cannot be parsed by int() directly and returns None.

        The coercion function calls int('42.9') which raises ValueError because
        int() only accepts integer strings, not decimal ones.
        """
        assert safe_int("42.9") is None

    def test_hex_string_returns_default(self) -> None:
        assert safe_int("0x2A") is None

    def test_comma_separated_number_returns_default(self) -> None:
        assert safe_int("1,000") is None

    def test_list_returns_default(self) -> None:
        assert safe_int([1, 2]) is None

    # -- Null handling ----------------------------------------------------------

    def test_none_returns_none(self) -> None:
        assert safe_int(None) is None

    def test_none_with_custom_default(self) -> None:
        assert safe_int(None, default=0) == 0

    def test_bool_false_returns_default(self) -> None:
        assert safe_int(False) is None

    def test_bool_true_returns_default(self) -> None:
        assert safe_int(True) is None


# =============================================================================
# safe_str — Unicode and malformed input edge cases
# =============================================================================


@pytest.mark.unit
class TestSafeStrEdgeCases:
    """Edge cases for safe_str beyond basic coercion tests."""

    # -- Unicode / multi-language -----------------------------------------------

    def test_chinese_characters(self) -> None:
        assert safe_str("化学品") == "化学品"

    def test_arabic_text(self) -> None:
        assert safe_str("مرحبا") == "مرحبا"

    def test_cyrillic_text(self) -> None:
        assert safe_str("аспирин") == "аспирин"

    def test_emoji_string(self) -> None:
        assert safe_str("🧬🔬") == "🧬🔬"

    def test_mixed_script_string(self) -> None:
        assert safe_str("aspirin аспирин") == "aspirin аспирин"

    def test_rtl_text_preserved(self) -> None:
        """RTL override character should be preserved as-is."""
        text = "\u202bHello"  # RIGHT-TO-LEFT EMBEDDING
        assert safe_str(text) == text

    def test_zero_width_space_preserved(self) -> None:
        """Zero-width spaces should survive conversion."""
        text = "a\u200bb"
        assert safe_str(text) == text

    def test_null_byte_in_string(self) -> None:
        """Null bytes inside a string should be preserved as-is."""
        text = "abc\x00def"
        assert safe_str(text) == text

    # -- Malformed inputs -------------------------------------------------------

    def test_empty_string_returns_empty_string(self) -> None:
        assert safe_str("") == ""

    def test_whitespace_only_preserved(self) -> None:
        """safe_str does NOT strip whitespace; that's normalize_string's job."""
        assert safe_str("   ") == "   "

    def test_large_integer_to_string(self) -> None:
        """Very large integers should convert cleanly."""
        result = safe_str(10**20)
        assert result == "100000000000000000000"

    def test_very_long_string_preserved(self) -> None:
        """Long strings should not be truncated."""
        long_str = "x" * 10_000
        assert safe_str(long_str) == long_str

    # -- Null handling ----------------------------------------------------------

    def test_none_returns_none(self) -> None:
        assert safe_str(None) is None

    def test_none_with_custom_default(self) -> None:
        assert safe_str(None, default="N/A") == "N/A"

    def test_none_with_empty_default(self) -> None:
        assert safe_str(None, default="") == ""


# =============================================================================
# normalize_for_hash — Unicode and edge cases
# =============================================================================


@pytest.mark.unit
class TestNormalizeForHashEdgeCases:
    """Edge cases for normalize_for_hash with Unicode and special values."""

    def test_unicode_string_values_stripped(self) -> None:
        """Unicode strings should still be stripped at boundaries."""
        record = {"name": "  аспирин  "}
        result = normalize_for_hash(record)
        assert result["name"] == "аспирин"

    def test_emoji_in_string_value(self) -> None:
        """Emoji characters in string values are valid and should be preserved."""
        record = {"label": "compound🧬"}
        result = normalize_for_hash(record)
        assert result["label"] == "compound🧬"

    def test_nested_dict_unicode(self) -> None:
        """Nested dict with Unicode values should be handled."""
        record = {"info": {"name": "  化学品  "}}
        result = normalize_for_hash(record)
        assert result["info"]["name"] == "化学品"

    def test_list_with_unicode_strings(self) -> None:
        """Lists containing Unicode strings should be normalized."""
        record = {"authors": ["  Smith  ", "  Иванов  "]}
        result = normalize_for_hash(record)
        assert result["authors"] == ["Smith", "Иванов"]

    def test_empty_dict_returns_empty(self) -> None:
        assert normalize_for_hash({}) == {}

    def test_only_meta_fields_returns_empty(self) -> None:
        """Record with only meta-fields should normalize to empty dict."""
        record = {
            "_ingestion_ts": "2025-01-01T00:00:00",
            "_run_id": "some-uuid",
            "_run_type": "incremental",
        }
        result = normalize_for_hash(record)
        assert result == {}

    def test_none_values_preserved(self) -> None:
        """Explicit None values in a record remain None after normalization."""
        record = {"value": None, "name": "aspirin"}
        result = normalize_for_hash(record)
        assert result["value"] is None
        assert result["name"] == "aspirin"

    def test_empty_string_stripped_to_empty(self) -> None:
        """An empty string stripped is still an empty string."""
        record = {"code": ""}
        result = normalize_for_hash(record)
        assert result["code"] == ""

    def test_boolean_value_preserved(self) -> None:
        """Boolean values (True/False) should pass through unchanged."""
        record = {"active": True, "deprecated": False}
        result = normalize_for_hash(record)
        assert result["active"] is True
        assert result["deprecated"] is False

    def test_integer_value_preserved(self) -> None:
        record = {"count": 42}
        result = normalize_for_hash(record)
        assert result["count"] == 42

    def test_nan_float_normalized_to_none(self) -> None:
        record = {"score": float("nan")}
        result = normalize_for_hash(record)
        assert result["score"] is None

    def test_inf_float_normalized_to_none(self) -> None:
        record = {"score": float("inf")}
        result = normalize_for_hash(record)
        assert result["score"] is None

    def test_list_with_null_entries(self) -> None:
        """Lists containing None entries should be preserved."""
        record = {"ids": [1, None, 3]}
        result = normalize_for_hash(record)
        assert result["ids"] == [1, None, 3]
