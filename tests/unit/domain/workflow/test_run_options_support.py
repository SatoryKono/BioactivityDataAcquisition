# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Branch coverage for immutable workflow run-option helpers."""

import pytest

from bioetl.domain.workflow._run_options_support import (
    prefer_override,
    prefer_stricter_persistence_profile,
    serialize_workflow_run_option_value,
)

pytestmark = pytest.mark.unit


def test_prefer_override_preserves_current_only_for_none_override() -> None:
    assert prefer_override("current", None) == "current"
    assert prefer_override("current", "override") == "override"
    assert prefer_override(None, "override") == "override"


@pytest.mark.parametrize(
    ("current", "override", "expected"),
    [
        (None, "replay_ready", "replay_ready"),
        ("replay_ready", None, "replay_ready"),
        ("forensic_grade", "replay_ready", "forensic_grade"),
        ("degraded_observable", "forensic_grade", "forensic_grade"),
        ("unknown", "degraded_observable", "degraded_observable"),
    ],
)
def test_prefer_stricter_persistence_profile(
    current: str | None, override: str | None, expected: str
) -> None:
    assert prefer_stricter_persistence_profile(current, override) == expected


def test_serialize_workflow_run_option_value_normalizes_only_owned_shapes() -> None:
    assert serialize_workflow_run_option_value(
        "multi_filter_ids", {"target": ("a", "b")}
    ) == {"target": ["a", "b"]}
    assert serialize_workflow_run_option_value("multi_filter_ids", "unchanged") == (
        "unchanged"
    )
    assert serialize_workflow_run_option_value("filter_ids", ("a", "b")) == ["a", "b"]
    assert serialize_workflow_run_option_value("filter_ids", ["a"]) == ["a"]
    assert serialize_workflow_run_option_value("other", ("a",)) == ("a",)
