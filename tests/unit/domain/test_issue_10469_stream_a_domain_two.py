"""Stream A domain residual coverage for #10469 / #10519."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.domain.behavior._author_helpers import (
    collect_affiliations_from_authors,
    deduplicate_case_insensitive,
    extract_affiliation_strings,
    hash_author_name,
    normalize_affiliation_string,
    normalize_to_surname_initial,
    parse_author_names,
    parse_author_string,
    try_parse_json_authors,
)
from bioetl.domain.composite.config_parsing import (
    optional_bool,
    optional_float,
    optional_int,
    optional_str,
    optional_str_tuple,
    require_float,
    require_int,
    require_object_dict,
    require_object_dict_sequence,
    require_str,
    require_str_mapping,
    require_str_tuple,
    str_key_mapping,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
    INPUT_SNAPSHOT_PUBLISHED_EVENT,
    RUN_STARTED_EVENT,
    STAGE_COMPLETED_EVENT,
    RunLedgerEntry,
    project_run_ledger_replay,
)
from bioetl.domain.mapping._publication_type_classification_support import (
    classify_chembl_type,
    classify_provider_type,
    classification_values,
    find_matching_classification_value,
    normalize_publication_classification_value,
    raw_publication_type,
)
from bioetl.domain.normalization.profiles._profile_value_normalizers import (
    normalize_profile_float,
    normalize_profile_governed_uppercase_vocabulary,
    normalize_profile_governed_vocabulary,
    normalize_profile_int,
    normalize_profile_json_string_list_vocabulary_strict,
)
from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    _handle_case_fields,
    _handle_enum_fields,
    _handle_null_fields,
    _handle_unit_fields,
    _normalizer_accepts_record_context,
)
from bioetl.domain.types import RunID

pytestmark = pytest.mark.unit

_TEST_RUN_ID = RunID(UUID("12345678-1234-5678-1234-567812345678"))


@dataclass(frozen=True)
class _PubType:
    unified_type: str
    subclass: str
    class_code: str
    specificity: int


def test_composite_config_parsing_covers_optional_and_error_branches() -> None:
    assert require_object_dict({"a": 1}, "cfg") == {"a": 1}
    with pytest.raises(ValueError, match="dictionary"):
        require_object_dict([1], "cfg")
    assert require_object_dict_sequence([{"a": 1}], "items") == ({"a": 1},)
    with pytest.raises(ValueError, match="must be a list"):
        require_object_dict_sequence("x", "items")
    with pytest.raises(ValueError, match="contain dictionaries"):
        require_object_dict_sequence(["x"], "items")

    assert require_str("ok", "name") == "ok"
    with pytest.raises(ValueError, match="non-empty string"):
        require_str("", "name")
    with pytest.raises(ValueError, match="non-empty string"):
        require_str(1, "name")
    assert optional_str(None, "name") is None
    with pytest.raises(ValueError, match="when provided"):
        optional_str("", "name")
    with pytest.raises(ValueError, match="when provided"):
        optional_str(1, "name")

    assert optional_bool(None, default=True, field_name="flag") is True
    assert optional_bool(False, default=True, field_name="flag") is False
    with pytest.raises(ValueError, match="boolean"):
        optional_bool("yes", default=True, field_name="flag")

    assert optional_int(None, "n", default=3) == 3
    assert require_int(None, "n", default=4) == 4
    assert require_int(8, "n") == 8
    with pytest.raises(ValueError, match="integer"):
        require_int(None, "n")
    with pytest.raises(ValueError, match="integer"):
        require_int(True, "n")
    with pytest.raises(ValueError, match="integer"):
        optional_int("1", "n")

    assert require_float(None, "x", default=1.5) == 1.5
    assert require_float("2.5", "x") == 2.5
    assert optional_float(None, "x") is None
    with pytest.raises(ValueError, match="number"):
        require_float(None, "x")
    with pytest.raises(ValueError, match="number"):
        require_float(True, "x")
    with pytest.raises(ValueError, match="number"):
        require_float("nope", "x")
    with pytest.raises(ValueError, match="finite"):
        require_float("inf", "x")

    assert str_key_mapping(None, "map") == {}
    with pytest.raises(ValueError, match="dictionary"):
        str_key_mapping("x", "map")
    assert require_str_mapping({"a": "b"}, "map") == {"a": "b"}
    with pytest.raises(ValueError, match="must be a string"):
        require_str_mapping({"a": 1}, "map")
    assert require_str_tuple(["a", "b"], "vals") == ("a", "b")
    with pytest.raises(ValueError, match="must be a list"):
        require_str_tuple("a", "vals")
    with pytest.raises(ValueError, match="non-empty strings"):
        require_str_tuple(["a", ""], "vals")
    assert optional_str_tuple(None, "vals") is None
    assert optional_str_tuple(["a"], "vals") == ("a",)


def test_publication_type_classification_edge_paths() -> None:
    journal = _PubType("journal", "article", "01", 10)
    review = _PubType("review", "article", "02", 20)
    lookup = {"journal-article": journal, "review": review}

    assert (
        classify_provider_type(lookup=None, raw_type="x", raw_types_list=None) is None
    )
    assert (
        classify_provider_type(
            lookup=lookup, raw_type=" Journal-Article ", raw_types_list=None
        )
        is journal
    )
    assert (
        classify_provider_type(lookup=lookup, raw_type=None, raw_types_list=["review"])
        is review
    )
    assert (
        classify_provider_type(lookup=lookup, raw_type=None, raw_types_list=None)
        is None
    )
    assert (
        classify_chembl_type(
            raw_type=None, raw_types_list=None, entry_by_unified_type={}
        )
        is None
    )
    assert (
        classify_chembl_type(
            raw_type=None,
            raw_types_list=["", "nope"],
            entry_by_unified_type={"journal": journal},
        )
        is None
    )

    assert raw_publication_type(raw_type="  ", raw_types_list=None) is None
    assert raw_publication_type(raw_type=None, raw_types_list=[" a ", "", "b"]) == "a|b"
    assert raw_publication_type(raw_type=None, raw_types_list=[]) is None
    assert (
        find_matching_classification_value("Journal", frozenset({"journal"}))
        == "journal"
    )
    assert find_matching_classification_value("x", frozenset({"journal"})) is None
    assert classification_values("publication_subclass", [journal]) == frozenset(
        {"article"}
    )
    with pytest.raises(ValueError, match="Unknown publication classification field"):
        classification_values("nope", [journal])
    assert (
        normalize_publication_classification_value(
            field_name="publication_type_unified",
            value=None,
            entries=[journal],
        )
        is None
    )
    assert (
        normalize_publication_classification_value(
            field_name="publication_type_unified",
            value=" JOURNAL ",
            entries=[journal],
        )
        == "journal"
    )


def test_author_helpers_cover_json_delimited_and_surname_formats() -> None:
    assert hash_author_name(" Ada ", "salt") == hash_author_name("ada", "salt")
    assert parse_author_names(123) == []  # type: ignore[arg-type]
    assert parse_author_names([" Ada ", {"name": "Bob"}, {"name": " "}, 1]) == [
        "Ada",
        "Bob",
    ]
    assert parse_author_string("") == []
    assert parse_author_string("[not-json") == ["[not-json"]
    assert try_parse_json_authors('{"name": "Ada"}') is None
    assert try_parse_json_authors('["Ada", {"name": "Bob"}]') == ["Ada", "Bob"]
    assert parse_author_string("Smith; Jones") == ["Smith", "Jones"]
    assert extract_affiliation_strings(
        [" MIT ", {"display_name": "Harvard"}, {"name": ""}, 1]
    ) == ["MIT", "Harvard"]
    assert normalize_affiliation_string("") is None
    assert normalize_affiliation_string("&lt;b&gt;MIT&lt;/b&gt;") == "MIT"
    assert deduplicate_case_insensitive(["MIT", "mit", "Harvard"]) == ["MIT", "Harvard"]
    assert normalize_to_surname_initial("  ") is None
    assert normalize_to_surname_initial("Smith") == "Smith"
    assert normalize_to_surname_initial("Smith,") == "Smith"
    assert normalize_to_surname_initial("Smith, John") == "Smith_J"
    assert normalize_to_surname_initial("Smith JA") == "Smith_J"
    assert normalize_to_surname_initial("X. Zhou") == "Zhou_X"
    assert normalize_to_surname_initial("Ada Lovelace") == "Lovelace_A"
    assert collect_affiliations_from_authors(
        [{"affiliations": "MIT"}, {"affiliations": ["Harvard"]}, {"name": "x"}]
    ) == ["MIT", "Harvard"]


def test_profile_value_normalizers_cover_unknown_and_coerce_paths() -> None:
    allowed = frozenset({"open", "closed"})
    assert normalize_profile_governed_vocabulary(1, allowed_values=allowed) == 1
    assert normalize_profile_governed_vocabulary("  ", allowed_values=allowed) is None
    assert (
        normalize_profile_governed_vocabulary("OPEN", allowed_values=allowed) == "open"
    )
    assert (
        normalize_profile_governed_vocabulary(
            "weird", allowed_values=allowed, preserve_unknown=True
        )
        == "weird"
    )
    assert (
        normalize_profile_governed_uppercase_vocabulary(
            "weird", allowed_values=allowed, preserve_unknown=True
        )
        == "WEIRD"
    )
    assert (
        normalize_profile_json_string_list_vocabulary_strict(1, allowed_values=allowed)
        is None
    )
    assert (
        normalize_profile_json_string_list_vocabulary_strict(
            "not-json", allowed_values=allowed
        )
        is None
    )
    assert (
        normalize_profile_json_string_list_vocabulary_strict(
            '{"a":1}', allowed_values=allowed
        )
        is None
    )
    assert (
        normalize_profile_json_string_list_vocabulary_strict(
            '["open","nope"]', allowed_values=allowed
        )
        is None
    )
    serialized = normalize_profile_json_string_list_vocabulary_strict(
        '["OPEN"]', allowed_values=allowed
    )
    assert serialized == '["open"]'
    assert normalize_profile_int(True) is True
    assert normalize_profile_int(2.0) == 2
    assert normalize_profile_int(float("nan")) is None
    assert normalize_profile_int(" 3 ") == 3
    assert normalize_profile_int("3.5") == "3.5"
    assert normalize_profile_int([1]) == [1]
    assert normalize_profile_float(True) is True
    assert normalize_profile_float(" 1.25 ") == 1.25
    assert normalize_profile_float("nope") == "nope"
    assert normalize_profile_float(float("inf")) is None
    assert normalize_profile_float({1}) == {1}


def test_standard_profile_rule_component_handlers() -> None:
    enum_rule = _handle_enum_fields("status", {"status": frozenset({"a"})})
    assert enum_rule is not None and enum_rule[0]("A") == "a"
    assert _handle_enum_fields("other", {"status": frozenset({"a"})}) is None
    case_rule = _handle_case_fields("name", {"name": None})
    assert case_rule is not None
    unit_rule = _handle_unit_fields("unit", frozenset({"unit"}))
    assert unit_rule is not None
    assert _handle_unit_fields("x", frozenset({"unit"})) is None
    null_rule = _handle_null_fields("note", frozenset({"note"}))
    assert null_rule is not None
    assert _handle_null_fields("x", frozenset({"note"})) is None

    def _with_record(value: object, record: object | None = None) -> object:
        return (value, record)

    def _with_kwargs(value: object, **_kwargs: object) -> object:
        return value

    assert _normalizer_accepts_record_context(_with_record) is True
    assert _normalizer_accepts_record_context(_with_kwargs) is True
    assert _normalizer_accepts_record_context(int) is False


def test_run_ledger_replay_covers_invalid_payload_branches() -> None:
    occurred = datetime(2026, 1, 1, tzinfo=UTC)

    def _entry(entry_id: str, event_type: str, **kwargs: object) -> RunLedgerEntry:
        return RunLedgerEntry(
            entry_id=entry_id,
            manifest_id="manifest-123",
            run_id=_TEST_RUN_ID,
            event_type=event_type,
            occurred_at=occurred,
            **kwargs,  # type: ignore[arg-type]
        )

    projection = project_run_ledger_replay(
        [
            _entry("e0", RUN_STARTED_EVENT),
            _entry("e1", STAGE_COMPLETED_EVENT, stage="preflight"),
            _entry("e2", COMPOSITE_DEPENDENCY_COMPLETED_EVENT, details="not-a-dict"),
            _entry(
                "e3",
                COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
                details={"dependency_name": "  "},
            ),
            _entry(
                "e4",
                COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
                details={
                    "dependency_name": "chembl",
                    "records_extracted": "nope",
                    "duration_seconds": object(),
                    "status": "success",
                },
            ),
            _entry(
                "e5", COMPOSITE_ENRICHER_COMPLETED_EVENT, details={"enricher_name": ""}
            ),
            _entry("e6", COMPOSITE_MERGE_COMPLETED_EVENT, details={}),
            _entry(
                "e7",
                INPUT_SNAPSHOT_PUBLISHED_EVENT,
                details={"snapshot_id": "s1"},
            ),
        ]
    )
    assert projection.replayed_entry_count == 8
    assert "chembl" in projection.completed_dependencies
    assert projection.merge_completed is None
    assert projection.input_snapshots == ()
    assert projection.projector_coverage_complete is False


def test_adapter_config_aliases_validation_and_circuit_breaker_merge() -> None:
    from bioetl.domain.adapter_config import AdapterConfig

    cfg = AdapterConfig(timeout=15)
    assert cfg.timeout == 15.0
    assert cfg.timeout_sec == 15.0
    matched = AdapterConfig(timeout=20, timeout_sec=20)
    assert matched.timeout_sec == 20.0
    with pytest.raises(ValueError, match="must match"):
        AdapterConfig(timeout=10, timeout_sec=20)
    with pytest.raises(TypeError, match="unexpected keyword"):
        AdapterConfig(unknown_alias=1)  # type: ignore[call-arg]
    merged = AdapterConfig(
        circuit_breaker=(9, 400),
        circuit_breaker_failure_threshold=7.0,  # type: ignore[arg-type]
        circuit_breaker_recovery_timeout=True,  # type: ignore[arg-type]
    )
    assert merged.circuit_breaker_failure_threshold == 7
    assert merged.circuit_breaker_recovery_timeout == 400
    assert AdapterConfig._as_optional_int(3.0) == 3
    assert AdapterConfig._as_optional_int(True) is None
    assert AdapterConfig._as_optional_float("1") is None
    with pytest.raises(ValueError, match="must be positive"):
        AdapterConfig(batch_size=0)
    with pytest.raises(ValueError, match="non-negative"):
        AdapterConfig(max_retries=-1)


def test_reason_catalog_resolve_unknown_and_mapping_roundtrip() -> None:
    from bioetl.domain.run_reports.reason_catalog import (
        catalog_as_mapping,
        catalog_from_mapping,
        normalize_reason_code,
    )

    empty = catalog_from_mapping({"version": "", "unknown_code": "", "reasons": "nope"})
    assert empty.resolve(None).code == "UNKNOWN_REASON"
    assert empty.family_for("missing") == "system"
    parsed = catalog_from_mapping(
        {
            "version": "v-test",
            "unknown_code": "CUSTOM_UNKNOWN",
            "reasons": [
                {"code": "  ", "family": "x"},
                {
                    "code": "MY_CODE",
                    "family": "dq",
                    "default_outcome": "quarantined",
                    "layer": "gold",
                    "description": "n",
                },
                "skip",
            ],
        }
    )
    assert parsed.resolve("MY_CODE").layer == "gold"
    assert parsed.resolve("nope").code == "CUSTOM_UNKNOWN"
    assert parsed.default_outcome_for(None) == "other"
    assert normalize_reason_code(None, parsed) == "CUSTOM_UNKNOWN"
    assert normalize_reason_code(" MY_CODE ", parsed) == "MY_CODE"
    assert normalize_reason_code("missing", parsed) == "CUSTOM_UNKNOWN"
    dumped = catalog_as_mapping(parsed)
    assert dumped["unknown_code"] == "CUSTOM_UNKNOWN"
    assert any(item["code"] == "MY_CODE" for item in dumped["reasons"])
