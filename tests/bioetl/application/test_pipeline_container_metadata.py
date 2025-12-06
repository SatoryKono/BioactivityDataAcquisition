from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
import pytest

from bioetl.application.container import PipelineContainer
from bioetl.domain.provider_registry import InMemoryProviderRegistry
from bioetl.domain.clients.base.output.contracts import (
    MetadataWriterABC,
    QualityReportABC,
    WriterABC,
    WriteResult,
)
from bioetl.domain.configs import DummyProviderConfig, PipelineConfig
from bioetl.domain.models import RunContext
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class RecordingWriter(WriterABC):
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    @property
    def atomic(self) -> bool:
        return False

    def write(
        self, df: pd.DataFrame, path: Path, *, column_order: list[str] | None = None
    ) -> WriteResult:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("data", encoding="utf-8")
        self.calls.append({"df": df, "path": path, "column_order": column_order})
        return WriteResult(
            path=path, row_count=len(df.index), duration_sec=0.0, checksum="stub"
        )

    def supports_format(self, fmt: str) -> bool:
        return True


class RecordingMetadataWriter(MetadataWriterABC):
    def __init__(self) -> None:
        self.meta_calls: list[dict[str, object]] = []
        self.qc_calls: list[dict[str, object]] = []
        self.checksum_calls: list[list[Path]] = []

    def write_meta(self, meta: dict, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("meta", encoding="utf-8")
        self.meta_calls.append({"meta": meta, "path": path})

    def write_qc_report(
        self, df: pd.DataFrame, path: Path, *, min_coverage: float | None = None
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("qc", encoding="utf-8")
        self.qc_calls.append({"df": df, "path": path, "min_coverage": min_coverage})

    def generate_checksums(self, paths: list[Path]) -> dict[str, str]:
        self.checksum_calls.append(list(paths))
        return {path.name: "chk" for path in paths}


class StubQualityReporter(QualityReportABC):
    def build_quality_report(
        self, df: pd.DataFrame, *, min_coverage: float
    ) -> pd.DataFrame:
        return pd.DataFrame({"column": ["a"], "null_count": [0]})

    def build_correlation_report(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({"column": ["a"], "a": [1.0]})


def _build_config(output_path: Path) -> PipelineConfig:
    return PipelineConfig(
        id="dummy.entity",
        provider="dummy",
        entity="entity",
        input_mode="auto_detect",
        input_path=None,
        output_path=str(output_path),
        batch_size=10,
        provider_config=DummyProviderConfig(
            base_url="https://example.com",  # type: ignore[arg-type]
            timeout_sec=1,
            max_retries=0,
            rate_limit_per_sec=1.0,
        ),
    )


@pytest.fixture()
def provider_registry() -> InMemoryProviderRegistry:
    return InMemoryProviderRegistry()


def test_container_uses_overridden_metadata_writer(
    run_context_factory: Callable[..., RunContext],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider_registry: InMemoryProviderRegistry,
) -> None:
    writer = RecordingWriter()
    metadata_writer = RecordingMetadataWriter()
    quality_reporter = StubQualityReporter()
    container = PipelineContainer(
        _build_config(tmp_path / "out"),
        writer=writer,
        metadata_writer=metadata_writer,
        quality_reporter=quality_reporter,
        provider_registry=provider_registry,
    )

    output_writer = container.get_output_writer()
    assert isinstance(output_writer, UnifiedOutputWriter)

    class InlineAtomic:
        def write_atomic(self, path: Path, write_fn) -> None:
            write_fn(path)

    monkeypatch.setattr(output_writer, "_atomic_op", InlineAtomic())

    run_context = run_context_factory()
    df = pd.DataFrame({"id": [1]})

    result = output_writer.write_result(
        df,
        Path(container.config.output_path),
        container.config.entity_name,
        run_context,
    )

    assert result.row_count == 1
    assert writer.calls
    assert metadata_writer.meta_calls
    assert metadata_writer.meta_calls[0]["path"].name == "meta.yaml"


def test_container_defaults_use_factories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider_registry: InMemoryProviderRegistry,
) -> None:
    default_writer_instance = RecordingWriter()
    default_metadata_writer_instance = RecordingMetadataWriter()
    default_quality_reporter_instance = StubQualityReporter()

    writer_calls = 0
    metadata_calls = 0
    quality_calls = 0

    def writer_factory() -> WriterABC:
        nonlocal writer_calls
        writer_calls += 1
        return default_writer_instance

    def metadata_factory() -> MetadataWriterABC:
        nonlocal metadata_calls
        metadata_calls += 1
        return default_metadata_writer_instance

    def quality_factory() -> QualityReportABC:
        nonlocal quality_calls
        quality_calls += 1
        return default_quality_reporter_instance

    monkeypatch.setattr("bioetl.application.container.default_writer", writer_factory)
    monkeypatch.setattr(
        "bioetl.application.container.default_metadata_writer", metadata_factory
    )
    monkeypatch.setattr(
        "bioetl.application.container.default_quality_reporter", quality_factory
    )

    container = PipelineContainer(
        _build_config(tmp_path / "defaults"), provider_registry=provider_registry
    )
    output_writer = container.get_output_writer()

    assert writer_calls == 1
    assert metadata_calls == 1
    assert quality_calls == 1
    assert isinstance(output_writer, UnifiedOutputWriter)
    assert output_writer._writer is default_writer_instance
    assert output_writer._metadata_writer is default_metadata_writer_instance
    assert output_writer._quality_reporter is default_quality_reporter_instance
