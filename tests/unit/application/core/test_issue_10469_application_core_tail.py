"""Focused tests for small application-core coverage residuals in #10469."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.core._batch_transformer_support import (
    resolve_transformer_bags,
)
from bioetl.application.core._checkpoint_payload import build_checkpoint_payload
from bioetl.application.core._quarantine_write_support import extract_record_id
from bioetl.application.core.batch_transformer_dq_thresholds import (
    ThresholdBreachReason,
    classify_dq_threshold_breach,
)
from bioetl.application.core.lifecycle.checkpoint_runtime import (
    validate_compatibility_policy,
)
from bioetl.application.core.lifecycle.shutdown import (
    ShutdownService,
    create_shutdown_service,
)
from bioetl.application.core.preflight.medallion_validator_idempotency import (
    validate_idempotency_contracts,
)
from bioetl.application.core.wiring.lazy_export_hooks import lazy_export_dir

pytestmark = pytest.mark.unit


def test_transformer_bags_reject_unknown_legacy_keyword() -> None:
    with pytest.raises(TypeError, match="unexpected keyword.*unknown"):
        resolve_transformer_bags(None, None, {"unknown": 1})


def test_checkpoint_payload_uses_plain_count_for_empty_memory_trace() -> None:
    memory_manager = SimpleNamespace(decision_trace_dicts=lambda: [])
    assert build_checkpoint_payload(7, memory_manager) == 7


def test_extract_record_id_returns_none_without_supported_identifier() -> None:
    assert extract_record_id({"unrelated": "value"}) is None


def test_dq_threshold_classification_returns_none_without_breach() -> None:
    assert (
        classify_dq_threshold_breach(
            error_rate=0.01,
            soft_threshold=0.1,
            hard_threshold=0.2,
        )
        is ThresholdBreachReason.NONE
    )


def test_checkpoint_policy_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="Unsupported checkpoint compatibility policy"):
        validate_compatibility_policy("unknown")


def test_shutdown_service_factory_preserves_collaborators() -> None:
    logger = MagicMock()
    metrics = MagicMock()
    service = create_shutdown_service(logger, metrics)
    assert isinstance(service, ShutdownService)
    assert service.logger is logger
    assert service.metrics is metrics


def test_disallowed_idempotency_contract_is_reported() -> None:
    errors = validate_idempotency_contracts(
        silver_mode="merge",
        gold_mode="merge",
        silver_contract="disallowed",
        gold_contract="primary_key_upsert",
    )
    assert errors
    assert errors[0].field == "sink.silver.idempotency_contract"
    assert errors[0].actual == "disallowed"


def test_lazy_export_directory_merges_namespace_and_exports() -> None:
    assert lazy_export_dir({"existing": object()}, ["exported"]) == [
        "existing",
        "exported",
    ]
