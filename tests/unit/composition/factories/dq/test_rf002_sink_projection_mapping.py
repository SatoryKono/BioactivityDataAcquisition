# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportGeneralTypeIssues=false
"""Owning composition test for PSC RF-002 DQ ingress→projection mapping (#12567).

Validates that live ``SinkLayerConfig`` dumps project into Bronze/Silver/Gold
extract DTOs without ``extra_forbidden``, while truly unknown projection keys
still fail.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.composition.factories.dq._context_resolver_support import (
    extract_single_dq_config_impl,
    project_sink_layer_to_extract_payload,
)
from bioetl.composition.factories.dq.context_resolver import extract_dq_configs
from bioetl.infrastructure.schemas.dq_report_config import (
    BronzeSinkConfig,
    GoldSinkConfig,
    SilverSinkConfig,
)
from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    SinkDQReportConfig,
    SinkLayerConfig,
)

pytestmark = pytest.mark.unit


def test_nested_projection_union_skips_none_and_rejects_non_models() -> None:
    from pydantic import BaseModel
    from bioetl.composition.factories.dq import _context_resolver_support as subject

    class Nested(BaseModel):
        enabled: bool = True

    assert subject._nested_basemodel_type(type(None) | Nested) is Nested
    assert subject._nested_basemodel_type(type(None) | int) is None


def test_projection_rejects_non_mapping_model_dump() -> None:
    from types import SimpleNamespace

    sink = SimpleNamespace(model_dump=lambda: [])
    with pytest.raises(TypeError, match="sink layer model_dump.*must return a mapping"):
        project_sink_layer_to_extract_payload(sink, BronzeSinkConfig)


def test_structural_projection_fallback_preserves_payload_on_subclass_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from bioetl.composition.factories.dq import _context_resolver_support as subject

    report = SimpleNamespace(enabled=True)
    payload = {"dq_report": {"enabled": True}}
    dump = MagicMock(return_value=payload)

    class StructuralConfig:
        model_validate = MagicMock(return_value=SimpleNamespace(dq_report=report))

    monkeypatch.setattr(
        subject, "issubclass", MagicMock(side_effect=TypeError), raising=False
    )
    result = subject.extract_single_dq_config_impl(
        {"bronze": SimpleNamespace(model_dump=dump)}, "bronze", StructuralConfig
    )
    assert result is report
    dump.assert_called_once_with()
    StructuralConfig.model_validate.assert_called_once_with(payload)


def _assert_extra_forbidden(exc_info: pytest.ExceptionInfo[ValidationError]) -> None:
    assert any(err["type"] == "extra_forbidden" for err in exc_info.value.errors())


def _live_sink_layers() -> dict[str, SinkLayerConfig]:
    """Ingress layers with fields that projection DTOs do not declare."""
    return {
        "bronze": SinkLayerConfig(
            enabled=True,
            path="data/output/bronze",
            format="jsonl",
            save_json=True,
            deterministic=True,
            flat_structure=False,
            dq_report=SinkDQReportConfig(enabled=True, format="json"),
        ),
        "silver": SinkLayerConfig(
            enabled=True,
            path="data/output/silver",
            format="delta",
            mode="merge",
            partition_by=["molecule_chembl_id"],
            save_metadata=True,
            flat_structure=True,
            dq_report=SinkDQReportConfig(
                enabled=True,
                output_path="reports/dq/silver",
                format="yaml",
            ),
        ),
        "gold": SinkLayerConfig(
            enabled=True,
            path="data/output/gold",
            format="delta",
            mode="overwrite",
            sort_by=["id"],
            deterministic=True,
            dq_report=SinkDQReportConfig(enabled=True, format="html"),
        ),
    }


@pytest.mark.parametrize(
    ("layer_name", "config_class"),
    [
        ("bronze", BronzeSinkConfig),
        ("silver", SilverSinkConfig),
        ("gold", GoldSinkConfig),
    ],
)
def test_project_sink_layer_accepts_live_ingress_dump(
    layer_name: str,
    config_class: type[BronzeSinkConfig | SilverSinkConfig | GoldSinkConfig],
) -> None:
    layers = _live_sink_layers()
    ingress = layers[layer_name]
    # Blind dump must fail under forbid (composition risk from plan §3.9).
    with pytest.raises(ValidationError) as blind:
        config_class.model_validate(ingress.model_dump())
    _assert_extra_forbidden(blind)

    payload = project_sink_layer_to_extract_payload(ingress, config_class)
    # Ingress-only keys must not leak into projection payload.
    for ingress_only in (
        "enabled",
        "save_json",
        "csv_export",
        "deterministic",
        "sort_by",
        "scd_config",
        "flat_structure",
        "idempotency_contract",
    ):
        assert ingress_only not in payload, ingress_only
    # Ingress dq_report has no checks — projection must not invent them here.
    dq = payload["dq_report"]
    assert isinstance(dq, dict)
    assert "checks" not in dq
    assert set(dq) <= {"enabled", "output_path", "format"}

    validated = config_class.model_validate(payload)
    assert validated.dq_report.enabled is True
    # Projection defaults still supply checks after validate.
    assert validated.dq_report.checks


def test_extract_single_dq_config_round_trip_from_sink_layer() -> None:
    layers = _live_sink_layers()
    bronze = extract_single_dq_config_impl(layers, "bronze", BronzeSinkConfig)
    silver = extract_single_dq_config_impl(layers, "silver", SilverSinkConfig)
    gold = extract_single_dq_config_impl(layers, "gold", GoldSinkConfig)
    assert bronze is not None and bronze.enabled is True
    assert silver is not None and silver.format == "yaml"
    assert gold is not None and gold.format == "html"
    # Ingress never carried checks; projection defaults remain.
    assert "checks" not in SinkDQReportConfig.model_fields
    assert bronze.checks
    assert silver.checks
    assert gold.checks


def test_extract_dq_configs_from_pipeline_like_sink_mapping() -> None:
    layers = _live_sink_layers()
    yaml_config = type("Yaml", (), {"sink": layers})()
    ctx = extract_dq_configs(yaml_config)
    assert ctx.bronze is not None
    assert ctx.silver is not None
    assert ctx.gold is not None


def test_projection_still_rejects_truly_unknown_keys() -> None:
    payload = project_sink_layer_to_extract_payload(
        _live_sink_layers()["bronze"],
        BronzeSinkConfig,
    )
    with pytest.raises(ValidationError) as exc_info:
        BronzeSinkConfig.model_validate({**payload, "rf002_unknown": 1})
    _assert_extra_forbidden(exc_info)
    with pytest.raises(ValidationError) as exc_info:
        BronzeSinkConfig.model_validate(
            {
                **payload,
                "dq_report": {**payload["dq_report"], "rf002_nested": True},
            }
        )
    _assert_extra_forbidden(exc_info)


def test_already_projection_dump_preserves_checks() -> None:
    """When input is already a projection DTO, checks survive the field map."""
    from bioetl.infrastructure.schemas.dq_report_config import SilverDQReportConfig

    silver = SilverSinkConfig(
        path="data/output/silver",
        dq_report=SilverDQReportConfig(
            enabled=True,
            checks=["record_count", "null_rate"],
        ),
    )
    payload = project_sink_layer_to_extract_payload(silver, SilverSinkConfig)
    assert payload["dq_report"]["checks"] == ["record_count", "null_rate"]
    validated = SilverSinkConfig.model_validate(payload)
    assert validated.dq_report.checks == ["record_count", "null_rate"]
