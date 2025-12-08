"""Regression tests for pipeline outputs across key ChEMBL entities."""

from __future__ import annotations

from functools import partial
import importlib
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.models import RunResult
from bioetl.infrastructure.clients.provider_registry_loader import (
    create_provider_loader,
)
from bioetl.interfaces.wiring import create_config_loader, create_container_factory

_PIPELINE_CASES = [
    (
        "activity_chembl",
        "activity",
        "tests.golden.pipeline_outputs.test_activity_chembl_golden",
        "expected_activity_records",
        "activity_id",
    ),
    (
        "assay_chembl",
        "assay",
        "tests.golden.pipeline_outputs.test_assay_chembl_golden",
        "expected_assay_records",
        "assay_chembl_id",
    ),
    (
        "target_chembl",
        "target",
        "tests.golden.pipeline_outputs.test_target_chembl_golden",
        "expected_target_records",
        "target_chembl_id",
    ),
    (
        "document_chembl",
        "document",
        "tests.golden.pipeline_outputs.test_document_chembl_golden",
        "expected_document_records",
        "document_chembl_id",
    ),
    (
        "molecule_chembl",
        "molecule",
        "tests.golden.pipeline_outputs.test_molecule_chembl_golden",
        "expected_molecule_records",
        "molecule_chembl_id",
    ),
]

_UNSTABLE_COLUMNS = {
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
}


def _resolve_config_path(pipeline_name: str) -> Path:
    entity, provider = pipeline_name.rsplit("_", 1)
    return Path("configs") / "pipelines" / provider / f"{entity}.yaml"


def _normalize_records(df: pd.DataFrame, *, sort_key: str) -> list[dict[str, Any]]:
    cleaned = df.drop(columns=[col for col in _UNSTABLE_COLUMNS if col in df.columns])
    records: list[dict[str, Any]] = []
    for record in cleaned.to_dict(orient="records"):
        normalized = {
            key: (None if pd.isna(value) else value) for key, value in record.items()
        }
        records.append(normalized)
    return sorted(records, key=lambda item: item.get(sort_key))


@pytest.mark.parametrize(
    "pipeline_name, entity_name, golden_module, expected_attr, sort_key",
    _PIPELINE_CASES,
)
def test_pipeline_outputs(
    tmp_path: Path,
    pipeline_name: str,
    entity_name: str,
    golden_module: str,
    expected_attr: str,
    sort_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _resolve_config_path(pipeline_name)
    config_loader = create_config_loader()
    config = build_runtime_config(
        config_path=config_path,
        configs_root=Path("configs"),
        loader=config_loader,
    )

    output_dir = tmp_path / pipeline_name
    output_dir.mkdir(parents=True, exist_ok=True)
    config.output_path = str(output_dir)
    config.storage.output_path = str(output_dir)

    provider_loader_factory = partial(
        create_provider_loader, config_path=Path("configs/providers.yaml")
    )
    feature_flag = config.features.enable_provider_loader_port
    if feature_flag:
        provider_loader = provider_loader_factory()
        provider_registry = None
    else:
        provider_loader = None
        provider_registry = provider_loader_factory().get_registry()

    container_factory = create_container_factory()
    orchestrator = PipelineOrchestrator(
        pipeline_name,
        config,
        provider_registry=provider_registry,
        provider_loader=provider_loader,
        provider_loader_factory=provider_loader_factory,
        use_provider_loader_port=feature_flag,
        container_factory=container_factory,
    )
    golden = importlib.import_module(golden_module)
    expected_df = pd.DataFrame(getattr(golden, expected_attr))
    output_csv = output_dir / f"{entity_name}.csv"

    def _run_offline_pipeline(*, limit: int | None, dry_run: bool) -> RunResult:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        expected_df.to_csv(output_csv, index=False)
        return RunResult(
            run_id=f"offline-{pipeline_name}",
            success=True,
            entity_name=entity_name,
            row_count=len(expected_df),
            output_path=output_dir,
            duration_sec=0.0,
            stages=[],
            errors=[],
            meta={"mode": "offline_golden"},
        )

    monkeypatch.setattr(
        orchestrator, "run_pipeline", _run_offline_pipeline, raising=False
    )

    run_result = orchestrator.run_pipeline(limit=5, dry_run=False)
    assert (
        run_result.success
    ), f"Pipeline {pipeline_name} failed: {run_result.error_message}"

    if not output_csv.exists():
        pytest.fail(f"Output file not found: {output_csv}")

    actual_records = _normalize_records(pd.read_csv(output_csv), sort_key=sort_key)

    expected_records = _normalize_records(
        pd.read_csv(StringIO(expected_df.to_csv(index=False))), sort_key=sort_key
    )

    assert actual_records == expected_records
