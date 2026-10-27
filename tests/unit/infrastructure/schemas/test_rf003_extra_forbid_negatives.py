# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportGeneralTypeIssues=false
"""Owning negative fixtures for PSC RF-003 (#12568).

Nested typo → ``extra_forbidden`` on strict boundaries; open-dict classification
keeps documented open semantics without weakening parent forbid.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from bioetl.infrastructure.schemas.dq_report_config import (
    BronzeDQReportConfig,
    BronzeSinkConfig,
)
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile
from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    GoldFiltersConfig,
    InputFilterYamlConfig,
    SilverFiltersConfig,
    SinkDQReportConfig,
    SinkLayerConfig,
)

pytestmark = pytest.mark.unit


def _assert_extra_forbidden(exc_info: pytest.ExceptionInfo[ValidationError]) -> None:
    assert any(err["type"] == "extra_forbidden" for err in exc_info.value.errors())


@pytest.mark.parametrize(
    ("model", "good", "typo_payload"),
    [
        (
            InputFilterYamlConfig,
            {"enabled": False},
            {"enabled": False, "rf003_input_typo": True},
        ),
        (
            SilverFiltersConfig,
            {},
            {"rf003_silver_typo": 1},
        ),
        (
            GoldFiltersConfig,
            {},
            {"rf003_gold_typo": 1},
        ),
        (
            SinkDQReportConfig,
            {"enabled": True, "format": "json"},
            {"enabled": True, "format": "json", "rf003_dq_typo": 1},
        ),
        (
            BronzeDQReportConfig,
            {"enabled": False},
            {"enabled": False, "rf003_bronze_dq_typo": 1},
        ),
        (
            BronzeSinkConfig,
            {"path": "data/output/bronze"},
            {"path": "data/output/bronze", "rf003_bronze_sink_typo": 1},
        ),
        (
            FilterConfigFile,
            {"version": "1.0.0"},
            {"version": "1.0.0", "rf003_filter_typo": True},
        ),
    ],
)
def test_rf003_strict_boundary_nested_typo_is_extra_forbidden(
    model: type[BaseModel],
    good: dict[str, Any],
    typo_payload: dict[str, Any],
) -> None:
    """Strict (forbid) leaves reject nested typos as extra_forbidden."""
    model.model_validate(good)
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate(typo_payload)
    _assert_extra_forbidden(exc_info)


def test_rf003_parent_strictness_intact_with_open_metadata_child() -> None:
    """Open metadata child does not weaken FilterConfigFile parent forbid."""
    good = {
        "version": "1.0.0",
        "metadata": {"policy": {"scope": "open"}},
    }
    FilterConfigFile.model_validate(good)
    with pytest.raises(ValidationError) as exc_info:
        FilterConfigFile.model_validate({**good, "not_a_filter_section": 1})
    _assert_extra_forbidden(exc_info)


def test_rf003_sink_layer_nested_dq_typo_is_extra_forbidden() -> None:
    """Nested sink.dq_report typo is extra_forbidden on the strict ingress path."""
    with pytest.raises(ValidationError) as exc_info:
        SinkLayerConfig.model_validate(
            {
                "path": "data/output/bronze",
                "format": "jsonl",
                "dq_report": {
                    "enabled": True,
                    "format": "json",
                    "rf003_nested_dq_typo": True,
                },
            }
        )
    _assert_extra_forbidden(exc_info)


def test_rf003_open_metadata_accepts_unknown_nested_keys() -> None:
    """Open-dict classification: FilterConfigFile.metadata keeps open semantics."""
    config = FilterConfigFile.model_validate(
        {
            "version": "1.0.0",
            "metadata": {"brand_new": {"a": 1}, "another": ["x"]},
        }
    )
    assert config.metadata["brand_new"]["a"] == 1
    assert config.metadata["another"] == ["x"]
