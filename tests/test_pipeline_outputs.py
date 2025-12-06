"""Regression tests for pipeline outputs across key ChEMBL entities."""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.errors import PipelineStageError
from bioetl.infrastructure.clients.provider_registry_loader import (
    load_provider_registry,
)

_PIPELINE_CASES = [
    (
        "activity_chembl",
        "activity",
        "tests.golden.pipeline_outputs.activity_chembl_golden",
        "expected_activity_records",
        "activity_id",
    ),
    (
        "assay_chembl",
        "assay",
        "tests.golden.pipeline_outputs.assay_chembl_golden",
        "expected_assay_records",
        "assay_chembl_id",
    ),
    (
        "target_chembl",
        "target",
        "tests.golden.pipeline_outputs.target_chembl_golden",
        "expected_target_records",
        "target_chembl_id",
    ),
    (
        "document_chembl",
        "document",
        "tests.golden.pipeline_outputs.document_chembl_golden",
        "expected_document_records",
        "document_chembl_id",
    ),
    (
        "testitem_chembl",
        "testitem",
        "tests.golden.pipeline_outputs.testitem_chembl_golden",
        "expected_testitem_records",
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
        normalized = {key: (None if pd.isna(value) else value) for key, value in record.items()}
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
) -> None:
    config_path = _resolve_config_path(pipeline_name)
    try:
        config = build_runtime_config(
            config_path=config_path,
            configs_root=Path("configs"),
        )
    except Exception as exc:  # noqa: BLE001 - propagate as xfail for missing configs
        pytest.xfail(f"Config unavailable for {pipeline_name}: {exc}")

    output_dir = tmp_path / pipeline_name
    output_dir.mkdir(parents=True, exist_ok=True)
    config.output_path = str(output_dir)
    config.storage.output_path = str(output_dir)

    provider_registry = load_provider_registry(
        config_path=Path("configs/providers.yaml")
    )

    orchestrator = PipelineOrchestrator(
        pipeline_name, config, provider_registry=provider_registry
    )
    try:
        run_result = orchestrator.run_pipeline(limit=5, dry_run=False)
    except PipelineStageError as exc:
        cause_text = str(exc.cause) if hasattr(exc, "cause") else ""
        if "Network access disabled" in cause_text:
            pytest.xfail(f"Network blocked for {pipeline_name}: {cause_text}")
        raise
    assert run_result.success, f"Pipeline {pipeline_name} failed: {run_result.error_message}"

    output_csv = output_dir / f"{entity_name}.csv"
    if not output_csv.exists():
        pytest.fail(f"Output file not found: {output_csv}")

    actual_records = _normalize_records(pd.read_csv(output_csv), sort_key=sort_key)

    golden = importlib.import_module(golden_module)
    expected_records = getattr(golden, expected_attr)

    assert actual_records == expected_records
