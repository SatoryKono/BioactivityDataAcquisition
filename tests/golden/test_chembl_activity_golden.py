"""Golden test for ChEMBL Activity pipeline (TS-004)."""

from datetime import datetime, timezone
from functools import partial
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pandas as pd
import pandas.testing as pd_testing
import pytest

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.pipelines.registry import get_pipeline_class
from bioetl.infrastructure.clients.chembl import ChemblExtractionServiceImpl
from bioetl.infrastructure.clients.provider_registry_loader import (
    create_provider_loader,
)
from bioetl.interfaces.container_factory import (
    build_default_container,
    create_config_loader,
)

sys.modules.setdefault("tqdm", MagicMock())


def _freeze_hash_service_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        "bioetl.domain.transform.hash_service.datetime",
        _FrozenDatetime,
    )
    # Мокируем datetime.now в models.py для фиксации started_at в RunContext
    monkeypatch.setattr(
        "bioetl.domain.models.datetime",
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

    config_loader = create_config_loader()
    config = build_runtime_config(
        config_path=Path("tests/fixtures/configs/chembl_activity_test.yaml"),
        configs_root=Path("tests/fixtures/configs"),
        loader=config_loader,
    )
    config.storage.output_path = str(tmp_path / "output")

    provider_loader_factory = partial(create_provider_loader)
    registry = provider_loader_factory().get_registry()
    container = build_default_container(
        config,
        provider_registry=registry,
    )
    pipeline_cls = get_pipeline_class("activity_chembl")
    pipeline = pipeline_cls(
        config=config,
        logger=container.get_logger(),
        validation_service=container.get_validation_service(),
        loader=container.get_loader(),
        extraction_service=container.get_extraction_service(),
        normalization_service=container.get_normalization_service(),
        record_source=container.get_record_source(
            extraction_service=container.get_extraction_service(),
            logger=container.get_logger(),
        ),
        hash_service=container.get_hash_service(),
    )
    monkeypatch.setattr(
        pipeline, "_should_skip_release_lookup", lambda: False, raising=False
    )

    pipeline.run(output_path=Path(config.storage.output_path))

    actual_path = Path(config.storage.output_path) / "activity.csv"
    expected_path = Path("qc/golden/chembl_activity/expected_output.csv")

    actual_df = pd.read_csv(actual_path)
    expected_df = pd.read_csv(expected_path)

    pd_testing.assert_frame_equal(actual_df, expected_df, check_dtype=False)
