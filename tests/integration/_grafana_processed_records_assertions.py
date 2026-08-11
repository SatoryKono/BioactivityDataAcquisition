# pyright: reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportIndexIssue=false
"""Focused assertions for Processed Records table field overrides."""

from __future__ import annotations


def assert_processed_records_field_overrides(
    processed: dict[str, object],
    *,
    expected_row_status_mappings: list[dict[str, object]],
) -> None:
    """Verify count, percentage, and hidden row-status field presentation."""
    overrides = processed.get("fieldConfig", {}).get("overrides", [])
    value_overrides = [
        override
        for override in overrides
        if override.get("matcher", {}).get("options") == "value"
    ]
    assert len(value_overrides) == 1
    value_properties = {
        prop.get("id"): prop.get("value")
        for prop in value_overrides[0].get("properties", [])
    }
    assert value_properties["custom.align"] == "right"
    assert value_properties["custom.width"] == 70
    assert value_properties["noValue"] == "UNKNOWN"
    assert value_properties["custom.cellOptions"] == {"type": "color-text"}
    assert value_properties.get("mappings", []) == []
    assert "color" not in value_properties
    assert "thresholds" not in value_properties
    assert "decimals" not in value_properties

    percentage_overrides = [
        override
        for override in overrides
        if override.get("matcher", {}).get("options") == "percentage"
    ]
    assert len(percentage_overrides) == 1
    percentage_properties = {
        prop.get("id"): prop.get("value")
        for prop in percentage_overrides[0].get("properties", [])
    }
    assert percentage_properties["custom.align"] == "right"
    assert percentage_properties["noValue"] == "UNKNOWN"
    assert percentage_properties["custom.cellOptions"] == {"type": "color-text"}
    assert percentage_properties.get("mappings", []) == []
    assert "color" not in percentage_properties
    assert "thresholds" not in percentage_properties

    row_status_overrides = [
        override
        for override in overrides
        if override.get("matcher", {}).get("options") == "row_status"
    ]
    assert len(row_status_overrides) == 1
    row_status_properties = {
        prop.get("id"): prop.get("value")
        for prop in row_status_overrides[0].get("properties", [])
    }
    assert row_status_properties["displayName"] == ""
    assert row_status_properties["custom.width"] == 1
    assert row_status_properties["custom.align"] == "center"
    assert row_status_properties["custom.cellOptions"] == {
        "type": "color-background",
        "applyToRow": True,
    }
    assert row_status_properties["mappings"] == expected_row_status_mappings
