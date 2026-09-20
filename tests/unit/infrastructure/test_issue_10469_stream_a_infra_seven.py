"""Remaining non-writer infrastructure residuals for #10469 / #10516."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.domain.exceptions import BioETLError, CriticalError
from bioetl.domain.types import ErrorType, RunID
from bioetl.domain.value_objects.dq_report import DQReportFormat, GoldDQCheckType
from bioetl.infrastructure.adr._adr_validators import (
    read_adr_text,
    validate_filename,
    validate_title,
)
from bioetl.infrastructure.adr.fs_adr_service import FilesystemAdrCatalog
from bioetl.infrastructure.checkpoint._local_checkpoint_sync import (
    LocalCheckpointSyncMixin,
)
from bioetl.infrastructure.errors.exception_mapper import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.schemas.composite_config import CompositeConfigFileSchema
from bioetl.infrastructure.schemas.dq_report_config import (
    BronzeDQReportConfig,
    GoldDQReportConfig,
)
from bioetl.infrastructure.security.pii_hasher import SaltConfig, Sha256PiiHasher
from bioetl.infrastructure.serialization import encoders as encoder_mod
from bioetl.infrastructure.serialization.encoders import (
    OrjsonEncoder,
    StdLibJsonEncoder,
    get_json_encoder,
    reset_encoder_cache,
)
from bioetl.infrastructure.storage.metadata_writer_operations_impl import (
    _MetadataWriterOperations,
)
from bioetl.infrastructure.storage.metadata_writer_public import MetadataWriter

pytestmark = pytest.mark.unit


def test_composite_config_rejects_local_gold_filters() -> None:
    payload = SimpleNamespace(gold_filters={"assay_type": ["B"]})
    with pytest.raises(ValueError, match="gold_filters are unsupported"):
        CompositeConfigFileSchema.reject_composite_local_gold_filters(payload)  # type: ignore[arg-type]


def test_exception_mapper_data_quality_generic_http_and_critical() -> None:
    mapper = DomainInfraExceptionMapper(logger=MagicMock())
    disposition = mapper.map_domain_to_infra_disposition(BioETLError("dq"))
    assert disposition.severity == "data_quality"
    assert disposition.retryable is False

    generic = mapper.map_to_domain_error(
        DomainErrorMappingInput(
            error=RuntimeError("not found"),
            provider="chembl",
            error_type=ErrorType.INVALID_DATA,
            status_code=404,
        )
    )
    assert generic.status_code == 404
    assert generic.reason_code == "ADAPTER_HTTP_ERROR"

    with pytest.raises(CriticalError, match="Critical chembl"):
        mapper.map_to_domain_error(
            DomainErrorMappingInput(
                error=RuntimeError("auth"),
                provider="chembl",
                error_type=ErrorType.AUTH_FAILURE,
            )
        )


def test_dq_report_config_enum_helpers() -> None:
    bronze = BronzeDQReportConfig()
    assert bronze.get_format_enum() is DQReportFormat.JSON
    gold = GoldDQReportConfig(
        checks=[GoldDQCheckType.COMPLETENESS.value, "not-a-check"]
    )
    assert gold.get_format_enum() is DQReportFormat.JSON
    assert gold.get_checks_enums() == [GoldDQCheckType.COMPLETENESS]


def test_json_encoder_orjson_missing_and_stdlib_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_encoder_cache()
    monkeypatch.setattr(encoder_mod, "orjson_available", False)
    monkeypatch.delenv("BIOETL_JSON_ENCODER", raising=False)
    with pytest.raises(ImportError, match="orjson is not installed"):
        OrjsonEncoder()
    with pytest.raises(ImportError, match="requested but not installed"):
        get_json_encoder("orjson")
    reset_encoder_cache()
    encoder = get_json_encoder()
    assert isinstance(encoder, StdLibJsonEncoder)
    reset_encoder_cache()


def test_adr_validators_and_catalog_error_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    issues: list[object] = []
    bad = tmp_path / "notes.md"
    bad.write_text("x", encoding="utf-8")
    assert validate_filename(bad, issues) is None  # type: ignore[arg-type]
    assert issues

    missing = tmp_path / "missing.md"
    text = read_adr_text(missing, 1, issues)  # type: ignore[arg-type]
    assert text is None

    title_issues: list[object] = []
    validate_title("# ADR-002 Title\n", 1, tmp_path / "ADR-001-x.md", title_issues)  # type: ignore[arg-type]
    assert title_issues

    catalog = FilesystemAdrCatalog(base_path=str(tmp_path))
    monkeypatch.setattr(
        "bioetl.infrastructure.adr.fs_adr_service.iter_adr_files",
        lambda _base: [tmp_path / "skip.md", tmp_path / "ADR-001-ok.md"],
    )

    def _parse(path: Path) -> tuple[int, str] | None:
        if path.name.startswith("ADR-"):
            return (1, "ok")
        return None

    monkeypatch.setattr(
        "bioetl.infrastructure.adr.fs_adr_service.parse_adr_filename",
        _parse,
    )
    ok = tmp_path / "ADR-001-ok.md"
    ok.write_bytes(b"\xff")
    listed = catalog.list_adrs()
    assert listed[0].number == 1

    with pytest.raises(FileNotFoundError, match="ADR-009"):
        catalog.get_adr(9)

    seen: set[int] = set()
    file_issues: list[object] = []
    catalog._validate_single_adr_file(bad, seen_numbers=seen, issues=file_issues)  # type: ignore[arg-type]
    assert file_issues


def test_pii_hasher_from_settings_without_optional_salts() -> None:
    empty = SimpleNamespace(
        pii_salt_current=None,
        pii_salt_next=None,
        pii_salt_rotation_active=False,
    )
    with pytest.raises(ValueError, match="cannot be empty"):
        SaltConfig.from_settings(empty)  # type: ignore[arg-type]

    settings = SimpleNamespace(
        pii_salt_current=SimpleNamespace(get_secret_value=lambda: "a" * 64),
        pii_salt_next=None,
        pii_salt_rotation_active=False,
    )
    config = SaltConfig.from_settings(settings)  # type: ignore[arg-type]
    assert len(config.current_salt) == 64
    assert config.next_salt is None
    hasher = Sha256PiiHasher.from_settings(settings)  # type: ignore[arg-type]
    assert hasher.get_salt_id()


def test_checkpoint_sync_empty_history_and_bad_manifest(tmp_path: Path) -> None:
    class _Sync(LocalCheckpointSyncMixin):
        def __init__(self, base_path: Path) -> None:
            self.base_path = base_path

    sync = _Sync(tmp_path)
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000001"))
    history = tmp_path / ".history" / "by_pipeline" / "pipe" / str(run_id)
    history.mkdir(parents=True)
    assert sync._load_for_run_sync("pipe", run_id) is None

    index = tmp_path / ".history" / "by_manifest" / "abc.json"
    index.parent.mkdir(parents=True)
    index.write_text("{}", encoding="utf-8")
    assert sync._load_for_manifest_id_sync("abc") is None

    index.write_text('{"history_path": "missing.json"}', encoding="utf-8")
    assert sync._load_for_manifest_id_sync("abc") is None


@pytest.mark.asyncio
async def test_metadata_writer_finalize_existing_and_public_wrappers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ops = _MetadataWriterOperations(
        logger=NoOpLogger(),
        metrics=None,
        retry_policy=MagicMock(),
        artifact_recorder_provider=lambda: None,
    )
    existing = SimpleNamespace(layer="silver")
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.metadata_writer_operations_impl._resolve_existing_metadata_path",
        lambda **_kwargs: Path("meta.yaml"),
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.metadata_writer_operations_impl.load_existing_metadata_model",
        AsyncMock(return_value=existing),
    )
    ops.write_metadata = AsyncMock(return_value="written.yaml")  # type: ignore[method-assign]
    finalized: list[object] = []

    def _apply(meta: object) -> None:
        finalized.append(meta)

    path = await ops.finalize_existing_layer_metadata(
        base_path=".",
        layer="silver",
        apply_finalization=_apply,
        table_name="activity",
    )
    assert path == "written.yaml"
    assert finalized == [existing]

    writer = MetadataWriter(NoOpLogger())
    writer._finalize_existing_layer_metadata = AsyncMock(return_value="sidecars.yaml")  # type: ignore[method-assign]
    writer._write_layer_metadata = AsyncMock(return_value="gold.yaml")  # type: ignore[method-assign]
    silver = await writer.finalize_silver_metadata(".", table_name="activity")
    gold = await writer.finalize_gold_metadata(".", table_name="activity")
    assert silver == "sidecars.yaml"
    assert gold == "sidecars.yaml"
