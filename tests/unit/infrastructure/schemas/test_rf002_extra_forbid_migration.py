# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportGeneralTypeIssues=false
"""Owning unit tests for PSC RF-002 ``extra=forbid`` migration (#12567).

Covers nested-path unknown-key checks by classification, runtime-only roots
outside ``generate-pipeline`` SCHEMAS, and BaseApiConfig connection-config
forbid (not wire).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from bioetl.infrastructure.schemas.base_schemas_chembl import BaseApiConfig
from bioetl.infrastructure.schemas.dq_report_config import (
    BronzeDQReportConfig,
    BronzeSinkConfig,
    GoldDQReportConfig,
    GoldSinkConfig,
    SilverDQReportConfig,
    SilverSinkConfig,
)
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile
from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    InputFilterYamlConfig,
    MaintenanceConfig,
    SinkDQReportConfig,
    SinkLayerConfig,
    TransformConfig,
)
from scripts.schema.generation.generate_pipeline_schema import SCHEMAS

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
PIPELINE_SCHEMA = ROOT / "configs" / "_schema" / "pipeline.json"

# root → runtime model → consumer → schema artifact | runtime-only
RF002_ROOT_MATRIX: tuple[dict[str, str | None], ...] = (
    {
        "root": "PipelineYamlConfig",
        "model": "bioetl.infrastructure.schemas.pipeline_config.PipelineYamlConfig",
        "consumer": "load_pipeline_config / entity YAML",
        "artifact": "configs/_schema/pipeline.json",
    },
    {
        "root": "FilterConfigFile",
        "model": "bioetl.infrastructure.schemas.filter_config.FilterConfigFile",
        "consumer": "standalone filter YAML / entity filter sections",
        "artifact": None,  # runtime-only (not in generate-pipeline SCHEMAS)
    },
    {
        "root": "BronzeDQReportConfig",
        "model": (
            "bioetl.infrastructure.schemas.dq_report_config.BronzeDQReportConfig"
        ),
        "consumer": "DQ composition projection (via BronzeSinkConfig)",
        "artifact": None,
    },
    {
        "root": "SilverDQReportConfig",
        "model": (
            "bioetl.infrastructure.schemas.dq_report_config.SilverDQReportConfig"
        ),
        "consumer": "DQ composition projection (via SilverSinkConfig)",
        "artifact": None,
    },
    {
        "root": "GoldDQReportConfig",
        "model": "bioetl.infrastructure.schemas.dq_report_config.GoldDQReportConfig",
        "consumer": "DQ composition projection (via GoldSinkConfig)",
        "artifact": None,
    },
    {
        "root": "BronzeSinkConfig",
        "model": "bioetl.infrastructure.schemas.dq_report_config.BronzeSinkConfig",
        "consumer": "project_sink_layer_to_extract_payload / extract_single_dq_config",
        "artifact": None,
    },
    {
        "root": "SilverSinkConfig",
        "model": "bioetl.infrastructure.schemas.dq_report_config.SilverSinkConfig",
        "consumer": "project_sink_layer_to_extract_payload / extract_single_dq_config",
        "artifact": None,
    },
    {
        "root": "GoldSinkConfig",
        "model": "bioetl.infrastructure.schemas.dq_report_config.GoldSinkConfig",
        "consumer": "project_sink_layer_to_extract_payload / extract_single_dq_config",
        "artifact": None,
    },
)


def _assert_extra_forbidden(exc_info: pytest.ExceptionInfo[ValidationError]) -> None:
    assert any(err["type"] == "extra_forbidden" for err in exc_info.value.errors())


def _good_and_unknown(
    model: type[BaseModel],
    good: dict[str, Any],
    *,
    unknown_key: str = "rf002_unknown_typo",
) -> None:
    model.model_validate(good)
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate({**good, unknown_key: 1})
    _assert_extra_forbidden(exc_info)


@pytest.mark.parametrize(
    ("model", "good"),
    [
        (SinkDQReportConfig, {"enabled": True, "format": "json"}),
        (MaintenanceConfig, {"auto_vacuum": False, "vacuum_retention_days": 7}),
        (TransformConfig, {"version": "1.0.0", "steps": ["normalize"]}),
        (
            InputFilterYamlConfig,
            {"enabled": False},
        ),
        (
            BaseApiConfig,
            {"base_url": "https://example.test", "rate_limit": 1.0, "timeout": 30},
        ),
        (
            BronzeDQReportConfig,
            {"enabled": True, "format": "json", "checks": ["record_count"]},
        ),
        (
            SilverDQReportConfig,
            {"enabled": True, "format": "json"},
        ),
        (
            GoldDQReportConfig,
            {"enabled": False},
        ),
        (
            BronzeSinkConfig,
            {"path": "data/output/bronze", "format": "jsonl"},
        ),
        (
            SilverSinkConfig,
            {"path": "data/output/silver", "format": "delta"},
        ),
        (
            GoldSinkConfig,
            {"path": "data/output/gold", "format": "delta"},
        ),
        (
            FilterConfigFile,
            {"version": "1.0.0"},
        ),
    ],
)
def test_rf002_strict_leaves_reject_unknown_keys(
    model: type[BaseModel],
    good: dict[str, Any],
) -> None:
    """Strict (forbid) leaves: good payload accepted; unknown key → extra_forbidden."""
    _good_and_unknown(model, good)


def test_sink_dq_ingress_rejects_checks_field() -> None:
    """YAML ingress SinkDQReportConfig must not credit projection ``checks``."""
    assert "checks" not in SinkDQReportConfig.model_fields
    with pytest.raises(ValidationError) as exc_info:
        SinkDQReportConfig.model_validate(
            {"enabled": True, "format": "json", "checks": ["record_count"]}
        )
    _assert_extra_forbidden(exc_info)


def test_parent_sink_layer_strictness_intact_with_nested_forbid() -> None:
    """Parent SinkLayerConfig remains forbid; unknown sibling rejected."""
    good = {
        "path": "data/output/bronze",
        "format": "jsonl",
        "dq_report": {"enabled": True, "format": "json"},
    }
    SinkLayerConfig.model_validate(good)
    with pytest.raises(ValidationError) as exc_info:
        SinkLayerConfig.model_validate({**good, "rf002_parent_typo": True})
    _assert_extra_forbidden(exc_info)
    # Nested ingress unknown also rejected.
    with pytest.raises(ValidationError) as exc_info:
        SinkLayerConfig.model_validate(
            {
                **good,
                "dq_report": {
                    "enabled": True,
                    "format": "json",
                    "rf002_nested_typo": 1,
                },
            }
        )
    _assert_extra_forbidden(exc_info)


def test_pipeline_schema_marks_migrated_nested_additional_properties_false() -> None:
    """Generator-covered nested leaves gain additionalProperties:false via stock gen."""
    schema = json.loads(PIPELINE_SCHEMA.read_text(encoding="utf-8"))
    defs = schema.get("$defs") or schema.get("definitions") or {}
    for name in (
        "SinkDQReportConfig",
        "MaintenanceConfig",
        "TransformConfig",
        "CsvExportConfig",
        "CircuitBreakerYamlConfig",
        "InputFilterYamlConfig",
    ):
        assert name in defs, name
        assert defs[name].get("additionalProperties") is False, name


def test_runtime_only_roots_absent_from_generate_pipeline_schemas() -> None:
    """FilterConfigFile / dq_report models stay runtime-only (not in SCHEMAS)."""
    schema_models = {cls.__name__ for cls in SCHEMAS.values()}
    assert "FilterConfigFile" not in schema_models
    for name in (
        "BronzeDQReportConfig",
        "SilverDQReportConfig",
        "GoldDQReportConfig",
        "BronzeSinkConfig",
        "SilverSinkConfig",
        "GoldSinkConfig",
    ):
        assert name not in schema_models
    # Runtime-only contract: unknown keys still rejected at Pydantic boundary.
    _good_and_unknown(FilterConfigFile, {"version": "1.0.0"})
    _good_and_unknown(
        BronzeDQReportConfig,
        {"enabled": False},
    )


def test_rf002_root_model_consumer_artifact_matrix() -> None:
    """Documented root→model→consumer→artifact|runtime-only matrix for RF-002."""
    generator_names = {Path(name).stem for name in SCHEMAS}
    assert generator_names == {"pipeline", "composite", "source", "dq"}
    for row in RF002_ROOT_MATRIX:
        if row["artifact"] is None:
            assert row["root"] not in {cls.__name__ for cls in SCHEMAS.values()}, row
        else:
            artifact = ROOT / str(row["artifact"])
            assert artifact.is_file(), row
            assert "pipeline" in generator_names
