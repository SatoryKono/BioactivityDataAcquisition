from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from bioetl.domain.clients.base.output.contracts import (
    QualityReportABC,
    WriterABC,
    WriteResult,
)
from bioetl.domain.configs import ClientConfig, DummyProviderConfig, PipelineConfig

# Provider registry module was removed
# from bioetl.domain.provider_registry import InMemoryProviderRegistry


class RecordingWriter(WriterABC):
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    @property
    def is_atomic(self) -> bool:
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

    def has_format_support(self, fmt: str) -> bool:
        return True


class RecordingMetadataWriter:
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

    def build_checksums(self, paths: list[Path]) -> dict[str, str]:
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
            client=ClientConfig(
                timeout_sec=1,
                max_retries=0,
                rate_limit_per_sec=1.0,
            ),
        ),
    )


@pytest.mark.skip(reason="Provider registry module was removed")
def test_container_uses_overridden_metadata_writer() -> None:
    """Legacy metadata writer override test disabled until registry returns."""


@pytest.mark.skip(reason="Provider registry module was removed")
def test_container_defaults_use_factories() -> None:
    """Legacy output writer factory test disabled until registry returns."""
