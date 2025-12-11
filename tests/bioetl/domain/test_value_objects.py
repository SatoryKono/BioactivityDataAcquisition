"""Tests for domain value objects."""

from pydantic import BaseModel
import pytest

from bioetl.domain.value_objects import HashDigest, StageName


class TestStageName:
    """Tests for StageName value object."""

    # --- Valid values ---

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("extract", "extract"),
            ("transform", "transform"),
            ("validate", "validate"),
            ("export", "export"),
        ],
    )
    def test_valid_values(self, value: str, expected: str) -> None:
        """Test that valid stage names are accepted."""
        stage = StageName(value)
        assert stage.value == expected
        assert str(stage) == expected

    # --- Case insensitivity ---

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("EXTRACT", "extract"),
            ("Extract", "extract"),
            ("TRANSFORM", "transform"),
            ("Transform", "transform"),
            ("VALIDATE", "validate"),
            ("Validate", "validate"),
            ("EXPORT", "export"),
            ("Export", "export"),
        ],
    )
    def test_case_insensitive(self, value: str, expected: str) -> None:
        """Test that stage names are case-insensitive."""
        stage = StageName(value)
        assert stage.value == expected

    # --- Alias support ---

    @pytest.mark.parametrize(
        "alias,canonical",
        [
            ("load", "export"),
            ("Load", "export"),
            ("LOAD", "export"),
        ],
    )
    def test_alias_load_to_export(self, alias: str, canonical: str) -> None:
        """Test that 'load' is an alias for 'export'."""
        stage = StageName(alias)
        assert stage.value == canonical
        assert stage == StageName.EXPORT

    # --- Invalid values ---

    @pytest.mark.parametrize(
        "invalid_value",
        [
            "fetch",
            "normalize",
            "invalid",
            "",
            "extract_data",
            "transform_records",
        ],
    )
    def test_invalid_values_raise_error(self, invalid_value: str) -> None:
        """Test that invalid stage names raise ValueError."""
        with pytest.raises(ValueError, match="Invalid stage name"):
            StageName(invalid_value)

    def test_invalid_type_raises_error(self) -> None:
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="StageName requires str"):
            StageName(123)  # type: ignore[arg-type]

    # --- Enum-like class constants ---

    def test_extract_constant(self) -> None:
        """Test StageName.EXTRACT constant."""
        assert StageName.EXTRACT.value == "extract"
        assert StageName.EXTRACT == StageName("extract")

    def test_transform_constant(self) -> None:
        """Test StageName.TRANSFORM constant."""
        assert StageName.TRANSFORM.value == "transform"
        assert StageName.TRANSFORM == StageName("transform")

    def test_validate_constant(self) -> None:
        """Test StageName.VALIDATE constant."""
        assert StageName.VALIDATE.value == "validate"
        assert StageName.VALIDATE == StageName("validate")

    def test_export_constant(self) -> None:
        """Test StageName.EXPORT constant."""
        assert StageName.EXPORT.value == "export"
        assert StageName.EXPORT == StageName("export")

    # --- all_values method ---

    def test_all_values(self) -> None:
        """Test all_values returns all allowed stage names."""
        values = StageName.all_values()
        assert values == frozenset({"extract", "transform", "validate", "export"})

    # --- Equality and hashing ---

    def test_equality_same_value(self) -> None:
        """Test that two StageName with same value are equal."""
        assert StageName("extract") == StageName("extract")
        assert StageName("EXTRACT") == StageName("extract")

    def test_equality_different_value(self) -> None:
        """Test that two StageName with different values are not equal."""
        assert StageName("extract") != StageName("transform")

    def test_equality_with_non_stagename(self) -> None:
        """Test that StageName is not equal to non-StageName."""
        assert (StageName("extract") == "extract") is False
        assert StageName("extract").__eq__("extract") is NotImplemented

    def test_hashable(self) -> None:
        """Test that StageName is hashable and can be used in sets."""
        stages = {StageName("extract"), StageName("EXTRACT"), StageName("transform")}
        assert len(stages) == 2  # extract and EXTRACT are the same

    def test_usable_as_dict_key(self) -> None:
        """Test that StageName can be used as dictionary key."""
        data = {StageName.EXTRACT: "extraction complete"}
        assert data[StageName("extract")] == "extraction complete"

    # --- String representation ---

    def test_str_representation(self) -> None:
        """Test __str__ returns the value."""
        assert str(StageName("extract")) == "extract"

    def test_repr_representation(self) -> None:
        """Test __repr__ returns a developer-friendly string."""
        assert repr(StageName("extract")) == "StageName('extract')"

    # --- Pydantic integration ---

    def test_pydantic_model_validation(self) -> None:
        """Test StageName works with Pydantic models."""

        class TestModel(BaseModel):
            stage: StageName

        model = TestModel(stage="extract")
        assert model.stage == StageName.EXTRACT
        assert model.stage.value == "extract"

    def test_pydantic_model_case_insensitive(self) -> None:
        """Test Pydantic model accepts case-insensitive values."""

        class TestModel(BaseModel):
            stage: StageName

        model = TestModel(stage="EXTRACT")
        assert model.stage.value == "extract"

    def test_pydantic_model_alias(self) -> None:
        """Test Pydantic model resolves aliases."""

        class TestModel(BaseModel):
            stage: StageName

        model = TestModel(stage="load")
        assert model.stage.value == "export"

    def test_pydantic_model_serialization(self) -> None:
        """Test StageName serializes to string in Pydantic."""

        class TestModel(BaseModel):
            stage: StageName

        model = TestModel(stage="extract")
        assert model.model_dump() == {"stage": "extract"}

    def test_pydantic_model_invalid_value(self) -> None:
        """Test Pydantic model rejects invalid stage names."""
        from pydantic import ValidationError

        class TestModel(BaseModel):
            stage: StageName

        with pytest.raises(ValidationError):
            TestModel(stage="invalid_stage")

    # --- Immutability ---

    def test_immutability(self) -> None:
        """Test that StageName instances are immutable."""
        stage = StageName("extract")
        with pytest.raises(AttributeError):
            stage._value = "transform"  # type: ignore[misc]


class TestHashDigest:
    """Tests for HashDigest value object."""

    # --- Valid hex hash samples ---
    VALID_BLAKE2B_256 = "a" * 64
    VALID_SHA256 = "b" * 64
    VALID_SHA512 = "c" * 128
    VALID_MD5 = "d" * 32

    # --- Basic creation with default algorithm ---

    def test_create_default_blake2b(self) -> None:
        """Test creating HashDigest with default blake2b_256 algorithm."""
        digest = HashDigest(self.VALID_BLAKE2B_256)
        assert digest.value == self.VALID_BLAKE2B_256
        assert digest.algorithm == "blake2b_256"

    def test_normalizes_to_lowercase(self) -> None:
        """Test that hex values are normalized to lowercase."""
        upper_hex = "A" * 64
        digest = HashDigest(upper_hex)
        assert digest.value == "a" * 64

    # --- Multi-algorithm support ---

    @pytest.mark.parametrize(
        "hex_value,algorithm,expected_len",
        [
            ("a" * 64, "blake2b_256", 64),
            ("b" * 64, "sha256", 64),
            ("c" * 128, "sha512", 128),
            ("d" * 32, "md5", 32),
        ],
    )
    def test_multiple_algorithms(
        self, hex_value: str, algorithm: str, expected_len: int
    ) -> None:
        """Test HashDigest supports multiple algorithms with correct lengths."""
        digest = HashDigest(hex_value, algorithm)
        assert digest.value == hex_value
        assert digest.algorithm == algorithm
        assert len(digest.value) == expected_len

    def test_unknown_algorithm_no_length_validation(self) -> None:
        """Test that unknown algorithms skip length validation."""
        digest = HashDigest("abc123", "custom_algo")
        assert digest.value == "abc123"
        assert digest.algorithm == "custom_algo"

    # --- Length validation ---

    @pytest.mark.parametrize(
        "hex_value,algorithm,expected_len",
        [
            ("a" * 63, "blake2b_256", 64),  # Too short
            ("a" * 65, "blake2b_256", 64),  # Too long
            ("b" * 127, "sha512", 128),  # Too short
            ("c" * 31, "md5", 32),  # Too short
        ],
    )
    def test_length_mismatch_raises_error(
        self, hex_value: str, algorithm: str, expected_len: int
    ) -> None:
        """Test that wrong length for known algorithm raises ValueError."""
        with pytest.raises(ValueError, match="length mismatch"):
            HashDigest(hex_value, algorithm)

    # --- Invalid hex values ---

    @pytest.mark.parametrize(
        "invalid_value",
        [
            "g" * 64,  # Invalid hex character
            "xyz123",  # Invalid characters
            "hello world",  # Spaces
            "",  # Empty string
        ],
    )
    def test_invalid_hex_raises_error(self, invalid_value: str) -> None:
        """Test that non-hex values raise ValueError."""
        with pytest.raises(ValueError, match="must be hex string"):
            HashDigest(invalid_value)

    # --- Factory methods ---

    def test_blake2b_256_factory(self) -> None:
        """Test blake2b_256 factory method."""
        digest = HashDigest.blake2b_256(self.VALID_BLAKE2B_256)
        assert digest.value == self.VALID_BLAKE2B_256
        assert digest.algorithm == "blake2b_256"
        assert digest.is_blake2b is True

    def test_from_hex_factory_default(self) -> None:
        """Test from_hex factory with default algorithm."""
        digest = HashDigest.from_hex(self.VALID_BLAKE2B_256)
        assert digest.value == self.VALID_BLAKE2B_256
        assert digest.algorithm == "blake2b_256"

    def test_from_hex_factory_with_algorithm(self) -> None:
        """Test from_hex factory with explicit algorithm."""
        digest = HashDigest.from_hex(self.VALID_MD5, "md5")
        assert digest.value == self.VALID_MD5
        assert digest.algorithm == "md5"

    # --- is_blake2b property ---

    def test_is_blake2b_true(self) -> None:
        """Test is_blake2b returns True for blake2b_256."""
        digest = HashDigest(self.VALID_BLAKE2B_256, "blake2b_256")
        assert digest.is_blake2b is True

    def test_is_blake2b_false(self) -> None:
        """Test is_blake2b returns False for other algorithms."""
        digest = HashDigest(self.VALID_MD5, "md5")
        assert digest.is_blake2b is False

    # --- Immutability ---

    def test_immutability_value(self) -> None:
        """Test that _value cannot be modified after creation."""
        digest = HashDigest(self.VALID_BLAKE2B_256)
        with pytest.raises(AttributeError, match="immutable"):
            digest._value = "b" * 64  # type: ignore[misc]

    def test_immutability_algorithm(self) -> None:
        """Test that _algorithm cannot be modified after creation."""
        digest = HashDigest(self.VALID_BLAKE2B_256)
        with pytest.raises(AttributeError, match="immutable"):
            digest._algorithm = "sha256"  # type: ignore[misc]

    def test_immutability_new_attribute(self) -> None:
        """Test that new attributes cannot be added."""
        digest = HashDigest(self.VALID_BLAKE2B_256)
        with pytest.raises(AttributeError):
            digest.new_attr = "test"  # type: ignore[attr-defined]

    # --- Equality and hashing ---

    def test_equality_same_value_and_algorithm(self) -> None:
        """Test equality when value and algorithm match."""
        d1 = HashDigest(self.VALID_BLAKE2B_256, "blake2b_256")
        d2 = HashDigest(self.VALID_BLAKE2B_256, "blake2b_256")
        assert d1 == d2

    def test_inequality_same_value_different_algorithm(self) -> None:
        """Test inequality when algorithms differ."""
        d1 = HashDigest(self.VALID_SHA256, "blake2b_256")
        d2 = HashDigest(self.VALID_SHA256, "sha256")
        assert d1 != d2

    def test_inequality_different_value(self) -> None:
        """Test inequality when values differ."""
        d1 = HashDigest("a" * 64)
        d2 = HashDigest("b" * 64)
        assert d1 != d2

    def test_equality_with_non_hashdigest(self) -> None:
        """Test that HashDigest is not equal to non-HashDigest."""
        digest = HashDigest(self.VALID_BLAKE2B_256)
        assert (digest == self.VALID_BLAKE2B_256) is False
        assert digest.__eq__(self.VALID_BLAKE2B_256) is NotImplemented

    def test_hashable_same_values(self) -> None:
        """Test that identical HashDigests have same hash."""
        d1 = HashDigest(self.VALID_BLAKE2B_256)
        d2 = HashDigest(self.VALID_BLAKE2B_256)
        assert hash(d1) == hash(d2)

    def test_usable_in_set(self) -> None:
        """Test that HashDigest can be used in sets."""
        digests = {
            HashDigest("a" * 64),
            HashDigest("a" * 64),  # Duplicate
            HashDigest("b" * 64),
        }
        assert len(digests) == 2

    def test_usable_as_dict_key(self) -> None:
        """Test that HashDigest can be used as dictionary key."""
        digest = HashDigest(self.VALID_BLAKE2B_256)
        data = {digest: "test_value"}
        assert data[HashDigest(self.VALID_BLAKE2B_256)] == "test_value"

    # --- String representation ---

    def test_str_representation(self) -> None:
        """Test __str__ returns the hex value."""
        digest = HashDigest(self.VALID_BLAKE2B_256)
        assert str(digest) == self.VALID_BLAKE2B_256

    def test_repr_representation(self) -> None:
        """Test __repr__ includes value and algorithm."""
        digest = HashDigest(self.VALID_BLAKE2B_256, "blake2b_256")
        expected = f"HashDigest('{self.VALID_BLAKE2B_256}', algorithm='blake2b_256')"
        assert repr(digest) == expected

    # --- Pydantic integration ---

    def test_pydantic_model_validation(self) -> None:
        """Test HashDigest works with Pydantic models."""

        class TestModel(BaseModel):
            digest: HashDigest

        model = TestModel(digest=self.VALID_BLAKE2B_256)
        assert model.digest.value == self.VALID_BLAKE2B_256
        assert model.digest.algorithm == "blake2b_256"

    def test_pydantic_model_serialization(self) -> None:
        """Test HashDigest serializes to string in Pydantic."""

        class TestModel(BaseModel):
            digest: HashDigest

        model = TestModel(digest=self.VALID_BLAKE2B_256)
        assert model.model_dump() == {"digest": self.VALID_BLAKE2B_256}

    def test_pydantic_model_invalid_value(self) -> None:
        """Test Pydantic model rejects invalid hash values."""
        from pydantic import ValidationError

        class TestModel(BaseModel):
            digest: HashDigest

        with pytest.raises(ValidationError):
            TestModel(digest="not_a_valid_hex")
