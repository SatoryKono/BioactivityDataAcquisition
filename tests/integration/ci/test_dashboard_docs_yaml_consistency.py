"""CI guard: dashboard docs must mirror (not redefine) YAML navigation contract."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

_YAML_PATH = Path("docs/03-guides/dashboards/contracts/navigation-links.yaml")
_SELECTOR_YAML_PATH = Path(
    "docs/03-guides/dashboards/contracts/selector-contracts.yaml"
)
_NAV_PATH = Path("docs/03-guides/dashboards/navigation-contract.md")
_VARS_PATH = Path("docs/03-guides/dashboards/variables-guide.md")
_VAR_REF_PATH = Path("docs/03-guides/dashboards/variable-reference.md")
_ARCH_PATH = Path("docs/03-guides/dashboards/selector-architecture.md")


@pytest.fixture(scope="module")
def contract() -> dict[str, object]:
    return yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))


def test_yaml_declares_single_normative_source(contract: dict[str, object]) -> None:
    marker = contract.get("normative_source")
    assert isinstance(marker, dict)
    assert marker.get("scope") == "link_vars_time_semantics"
    assert marker.get("authority") == "single_source_of_truth"
    assert isinstance(marker.get("narrative_minimal"), str)


def test_docs_reference_yaml_contract_keys(contract: dict[str, object]) -> None:
    nav_text = _NAV_PATH.read_text(encoding="utf-8")
    vars_text = _VARS_PATH.read_text(encoding="utf-8")
    var_ref_text = _VAR_REF_PATH.read_text(encoding="utf-8")
    arch_text = _ARCH_PATH.read_text(encoding="utf-8")
    selector_contract = yaml.safe_load(_SELECTOR_YAML_PATH.read_text(encoding="utf-8"))

    required_keys = [
        "required_link_vars_by_target_uid",
        "allowed_dashboard_link_vars",
        "forbidden_dashboard_link_vars_by_target_uid",
        "time_handoff_requirements",
        "default_time_refresh_policy",
    ]

    assert "navigation-links.yaml" in nav_text
    assert "navigation-links.yaml" in vars_text
    assert "selector-contracts.yaml" in vars_text
    assert "selector-contracts.yaml" in var_ref_text
    assert "selector-contracts.yaml" in arch_text

    for key in required_keys:
        assert key in vars_text or key in nav_text
        assert key in contract

    assert isinstance(selector_contract, dict)
    for key in (
        "selector_taxonomy",
        "dashboard_families",
        "shipped_selector_registry",
        "ship_now_selector_contract_by_uid",
        "hidden_handoff_contract",
    ):
        assert key in selector_contract


def test_docs_do_not_redefine_normative_tables() -> None:
    nav_text = _NAV_PATH.read_text(encoding="utf-8")
    assert "| Dashboard UID | Обязательные top-level links" not in nav_text
    assert "| Dashboard UID | First Action panel ID" not in nav_text
