"""Behavior coverage for remaining two-line infrastructure residuals in #10469."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl._health_probe import (
    handle_chembl_health_response,
)
from bioetl.infrastructure.adapters.chembl.health import ChemblHealthMixin
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader
from bioetl.infrastructure.adapters.input.idmapping_csv_reader_adapter import (
    IDMappingCsvReaderAdapter,
)
from bioetl.infrastructure.config.enum_loader_adapter import FileSystemEnumLoader
from bioetl.infrastructure.quality.debt_scorecard import _iter_registry_entries
from bioetl.infrastructure.schemas.composite_validation import (
    CompositeDQSchema,
    DQOverrideSchema,
)
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile
from bioetl.infrastructure.storage.support import _atomic_replace
from bioetl.infrastructure.storage.support._atomic_replace import AtomicWriteError
from bioetl.infrastructure.storage.writer_common import (
    iterate_write_targets,
    validate_write_versions,
)

pytestmark = pytest.mark.unit


def test_chembl_non_200_health_response_is_degraded() -> None:
    response = SimpleNamespace(status_code=503)
    logger = MagicMock()
    assert (
        handle_chembl_health_response(
            response=response, provider_name="chembl", logger=logger
        )
        is HealthStatus.DEGRADED
    )
    logger.warning.assert_called_once_with(
        "health_check_degraded",
        provider="chembl",
        reason="non_200_response",
        status_code=503,
    )


def test_chembl_health_mixin_exposes_status_and_circuit_stats() -> None:
    error = SimpleNamespace(response=SimpleNamespace(status_code=429))
    assert ChemblHealthMixin._extract_http_status_code(error) == 429
    host = ChemblHealthMixin()
    host.http_client = SimpleNamespace(
        circuit_breaker=SimpleNamespace(
            get_failure_count=lambda: 2,
            get_state=lambda: SimpleNamespace(value="closed"),
        )
    )
    host._get_effective_health_status = lambda: HealthStatus.DEGRADED  # type: ignore[method-assign]
    assert host.get_error_stats() == {
        "circuit_breaker_failures": 2,
        "circuit_breaker_state": "closed",
        "health_status": "DEGRADED",
    }


def test_csv_reader_wraps_polars_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "ids.csv"
    source.write_text("id\n1\n", encoding="utf-8")
    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.input.csv_filter_reader.pl.read_csv",
        MagicMock(side_effect=OSError("unreadable")),
    )
    with pytest.raises(ValueError, match="Failed to read CSV file: unreadable"):
        CsvFilterReader()._read_csv_dataframe(str(source))


@pytest.mark.asyncio
async def test_idmapping_reader_health_is_healthy() -> None:
    assert await IDMappingCsvReaderAdapter().health_check() is HealthStatus.HEALTHY


def test_enum_loader_delegates_default_and_explicit_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bioetl.infrastructure.config import enum_file_loader

    loader = MagicMock(side_effect=[{"default": True}, {"explicit": True}])
    monkeypatch.setattr(enum_file_loader, "load_provider_enums_from_file", loader)
    assert FileSystemEnumLoader().load_provider_enums("chembl") == {"default": True}
    explicit = FileSystemEnumLoader(tmp_path)
    assert explicit.load_chembl_enums() == {"explicit": True}
    assert loader.call_args_list[1].args[1] == tmp_path / "configs/enums/chembl.yaml"


def test_debt_scorecard_registry_iteration_skips_invalid_shapes() -> None:
    assert _iter_registry_entries({"registries": []}) == ()
    assert _iter_registry_entries(
        {"registries": {"valid": [], "mixed": {"skip": 1, "keep": {"id": "x"}}}}
    ) == ({"id": "x"},)


def test_composite_threshold_schemas_reject_inverted_ranges() -> None:
    with pytest.raises(ValueError, match="less than hard_fail_threshold"):
        DQOverrideSchema(soft_fail_threshold=0.5, hard_fail_threshold=0.5)
    with pytest.raises(ValueError, match="must be <"):
        CompositeDQSchema(soft_fail_threshold=0.7, hard_fail_threshold=0.2)


def test_filter_config_validators_cover_passthrough_and_bad_value() -> None:
    marker = object()
    assert FilterConfigFile.reject_semantic_silver_filters(marker) is marker
    with pytest.raises(ValueError, match=r"must be str\|int\|bool"):
        FilterConfigFile.validate_extraction_params({"bad": []})  # type: ignore[dict-item]


def test_writer_common_rejects_empty_and_mismatched_versions() -> None:
    with pytest.raises(ValueError, match="at least one write version"):
        validate_write_versions([])
    with pytest.raises(ValueError, match="length mismatch"):
        iterate_write_targets(["v1"], [])


def test_atomic_replace_rejects_escape_and_terminal_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(AtomicWriteError, match="parent does not match"):
        _atomic_replace._confined_replace_pair(
            tmp_path / "temp" / "x", tmp_path / "target" / "x"
        )

    error = OSError("locked")
    with pytest.raises(OSError, match="locked"):
        _atomic_replace._retry_delay_or_raise(
            error,
            retry_policy=MagicMock(),
            retry_count=0,
        )

    monkeypatch.setattr(_atomic_replace, "_is_retryable_replace_error", lambda _e: True)
    policy = MagicMock()
    policy.should_retry.return_value = False
    with pytest.raises(OSError, match="locked"):
        _atomic_replace._retry_delay_or_raise(
            error,
            retry_policy=policy,
            retry_count=1,
        )
