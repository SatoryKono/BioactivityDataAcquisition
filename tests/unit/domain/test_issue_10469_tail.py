"""Focused domain tests for one-line coverage residuals in issue #10469."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

import bioetl.domain.behavior as behavior_facade
import bioetl.domain.config as config_facade
import bioetl.domain.exceptions as exceptions_facade
import bioetl.domain.filtering as filtering_facade
import bioetl.domain.mapping.publication_controlled_vocabulary as publication_vocabulary
import bioetl.domain.normalization.profiles as profiles_facade
from bioetl.domain.behavior._dq_serializer_yaml import format_yaml_scalar
from bioetl.domain.behavior.composite_metadata_cv import summarize_composite_cv_dq
from bioetl.domain.behavior.cross_validation_validator import _collect_blocker_issues
from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.composite.config_cross_validation import _require_finite_number
from bioetl.domain.composite.lineage import _status_error_message
from bioetl.domain.config.table import _normalize_idempotency_contract
from bioetl.domain.filtering.silver_filter_identity import (
    DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE,
    normalize_silver_filter_compatibility_mode,
)
from bioetl.domain.mapping.publication_controlled_vocabulary import (
    PublicationControlledVocabularyRegistry,
    initialize_publication_controlled_vocabulary,
    is_publication_controlled_vocabulary_initialized,
)
from bioetl.domain.models._metadata_common import validate_utc_datetime
from bioetl.domain.types.gold_contracts_scd import ScdConfig
from bioetl.domain.types.validation_severity import ValidationSeverity

pytestmark = pytest.mark.unit


class _StringableValue:
    def __str__(self) -> str:
        return "value with space"


@pytest.mark.parametrize(
    "facade",
    [
        behavior_facade,
        config_facade,
        exceptions_facade,
        filtering_facade,
        profiles_facade,
    ],
)
def test_domain_lazy_facade_directory_contains_public_exports(facade: Any) -> None:
    assert set(facade.__all__).issubset(facade.__dir__())


def test_yaml_scalar_falls_back_to_string_representation() -> None:
    assert format_yaml_scalar(_StringableValue()) == '"value with space"'


def test_empty_composite_cv_summary_is_explicitly_signal_free() -> None:
    assert summarize_composite_cv_dq([]) == {
        "has_signal": False,
        "warning_records": 0,
        "error_records": 0,
        "quarantine_records": 0,
        "validation_passed": True,
        "rule_provenance": [],
    }


def test_collect_blocker_issues_filters_other_severities() -> None:
    blocker = SimpleNamespace(severity=ValidationSeverity.BLOCKER)
    warning = SimpleNamespace(severity=ValidationSeverity.WARNING)
    assert _collect_blocker_issues(cast(Any, [warning, blocker])) == [blocker]


def test_dq_metrics_empty_batch_has_no_incoming_fields() -> None:
    assert DQMetricsCalculator._extract_incoming_fields([]) == set()


def test_cross_validation_threshold_rejects_bool() -> None:
    with pytest.raises(ValueError, match="must be a number"):
        _require_finite_number(True, "threshold")


def test_lineage_error_message_stringifies_non_string_value() -> None:
    assert _status_error_message({"error_message": 404}) == "404"


def test_blank_idempotency_contract_normalizes_to_none() -> None:
    assert _normalize_idempotency_contract("  ") is None


def test_missing_silver_filter_mode_uses_compatibility_default() -> None:
    assert (
        normalize_silver_filter_compatibility_mode(None)
        == DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE
    )


def test_publication_vocabulary_reports_registry_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(publication_vocabulary, "_registry", None)
    assert is_publication_controlled_vocabulary_initialized() is False

    initialize_publication_controlled_vocabulary(
        PublicationControlledVocabularyRegistry(allowed_values_by_field={})
    )

    assert is_publication_controlled_vocabulary_initialized() is True


def test_metadata_datetime_rejects_naive_value() -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        validate_utc_datetime(datetime(2026, 1, 1))


def test_scd_config_rejects_non_positive_type() -> None:
    with pytest.raises(ValueError, match="scd_type must be positive"):
        ScdConfig(scd_type=0)
