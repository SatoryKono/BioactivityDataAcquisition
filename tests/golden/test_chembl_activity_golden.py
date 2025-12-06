"""Golden test for ChEMBL Activity pipeline (TS-004)."""
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pandas as pd
import pandas.testing as pd_testing
import pytest

sys.modules.setdefault("tqdm", MagicMock())

from bioetl.application.container import build_pipeline_dependencies  # noqa: E402
from bioetl.application.pipelines.registry import get_pipeline_class  # noqa: E402
from bioetl.application.services.chembl_extraction import ChemblExtractionServiceImpl  # noqa: E402
from bioetl.infrastructure.config.resolver import ConfigResolver  # noqa: E402


def _freeze_hash_service_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        "bioetl.domain.transform.hash_service.datetime",
        _FrozenDatetime,
    )


@pytest.mark.golden
def test_chembl_activity_golden(tmp_path, monkeypatch):
    """TS-004: pipeline output matches golden snapshot."""
    monkeypatch.setenv(
        "BIOETL_CONFIG_DIR",
        str(Path("tests/fixtures/configs").resolve()),
    )
    monkeypatch.setattr(
        ChemblExtractionServiceImpl,
        "get_release_version",
        lambda self: "chembl_golden",
    )
    _freeze_hash_service_clock(monkeypatch)

    resolver = ConfigResolver()
    config = resolver.resolve("chembl_activity_test.yaml")
    config.storage.output_path = str(tmp_path / "output")

    container = build_pipeline_dependencies(config)
    pipeline_cls = get_pipeline_class("activity_chembl")
    pipeline = pipeline_cls(
        config=config,
        logger=container.get_logger(),
        validation_service=container.get_validation_service(),
        output_writer=container.get_output_writer(),
        extraction_service=container.get_extraction_service(),
        record_source=container.get_record_source(
            extraction_service=container.get_extraction_service(),
            logger=container.get_logger(),
        ),
        hash_service=container.get_hash_service(),
    )

    pipeline.run(output_path=Path(config.storage.output_path))

    actual_path = Path(config.storage.output_path) / "activity.csv"
    expected_path = Path("qc/golden/chembl_activity/expected_output.csv")

    actual_df = pd.read_csv(actual_path)
    expected_df = pd.read_csv(expected_path)

    pd_testing.assert_frame_equal(actual_df, expected_df, check_dtype=False)
