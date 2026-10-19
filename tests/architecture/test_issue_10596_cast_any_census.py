# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface - product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""AUD-006 (#10596) acceptance: cast(Any) census, Protocol host, shrink ratchet."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa.report_cast_any_typing_census import (
    JUSTIFICATION_CATEGORIES,
    UNJUSTIFIED_CATEGORY,
    classify_statement_window,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CENSUS_JSON = ROOT / "reports" / "quality" / "cast-any-typing-census.json"
CENSUS_MD = ROOT / "reports" / "quality" / "cast-any-typing-census.md"
BUDGET = ROOT / "configs" / "quality" / "cast_any_unjustified_budget.yaml"
GENERATOR = ROOT / "scripts" / "engineering" / "qa" / "report_cast_any_typing_census.py"
APPLICATION_CORE = ROOT / "src" / "bioetl" / "application" / "core"
PROTOCOL_HOST_MODULE = APPLICATION_CORE / "_record_normalization_mapping.py"
PROTOCOL_CONTRACT_MODULE = APPLICATION_CORE / "_record_normalization_contract.py"
PROTOCOL_HOST_NAME = "_RecordNormalizationMappingHost"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_10596_census_artifacts_exist_with_counts() -> None:
    assert GENERATOR.exists()
    assert CENSUS_JSON.exists()
    assert CENSUS_MD.exists()
    payload = _load_json(CENSUS_JSON)
    assert payload["schema_version"] == "cast-any-typing-census-v1"
    assert payload["linked_issue"] == "#10596"
    summary = payload["summary"]
    assert isinstance(summary["justified_count"], int)
    assert isinstance(summary["unjustified_count"], int)
    assert (
        summary["justified_count"] + summary["unjustified_count"]
        == summary["total_cast_any_count"]
    )
    assert summary["total_cast_any_count"] == len(payload["findings"])
    assert payload["top_files"]
    markdown = CENSUS_MD.read_text(encoding="utf-8")
    assert f"- justified_count: {summary['justified_count']}" in markdown
    assert f"- unjustified_count: {summary['unjustified_count']}" in markdown


def test_issue_10596_census_findings_are_deterministically_sorted() -> None:
    payload = _load_json(CENSUS_JSON)
    keys = [(str(row["path"]), int(row["line"])) for row in payload["findings"]]
    assert keys == sorted(keys)
    assert "generated_at" not in payload
    assert "generated_at_utc" not in payload


@pytest.mark.parametrize(
    ("window", "expected_justified"),
    [
        ("x: str = cast(Any, None)  # Any: host attr default (PD3)", True),
        ("x: str = cast(\n    Any, None\n)  # Any: host attr default (PD6)", True),
        ("return cast(Any, obj)  # Any: mixin host", True),
        ("payload = cast(Any, raw)  # Any: JSON payload", True),
        ("value = cast(Any, x)  # TYPE-002 justified boundary", True),
        ("return as_mixin_host(self).attr", True),
        ("x: str = cast(Any, None)  # Any: host default (PD4)", False),
        ("table = cast(Any, pa_table)  # Any: pyarrow duck-type", False),
        ("table = cast(Any, pa_table)", False),
    ],
)
def test_issue_10596_classification_rules(
    window: str, expected_justified: bool
) -> None:
    category = classify_statement_window(window)
    assert (category != UNJUSTIFIED_CATEGORY) is expected_justified
    if expected_justified and "as_mixin_host" not in window:
        assert category in {name for name, _ in JUSTIFICATION_CATEGORIES}


def _protocol_class_names(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id == "Protocol")
            or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
            for base in node.bases
        )
    }


def test_issue_10596_record_normalization_mapping_uses_protocol_host() -> None:
    assert PROTOCOL_HOST_MODULE.exists()
    assert PROTOCOL_CONTRACT_MODULE.exists()
    source = PROTOCOL_HOST_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    contract_tree = ast.parse(PROTOCOL_CONTRACT_MODULE.read_text(encoding="utf-8"))
    assert PROTOCOL_HOST_NAME in _protocol_class_names(contract_tree)
    imported_names = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "bioetl.application.core._record_normalization_contract"
        for alias in node.names
    }
    assert PROTOCOL_HOST_NAME in imported_names
    cast_any_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "cast"
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "Any"
    ]
    assert cast_any_calls == []

    mixin = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "RecordNormalizationMappingMixin"
    )
    class_level_defaults = [
        node
        for node in mixin.body
        if isinstance(node, ast.AnnAssign) and node.value is not None
    ]
    assert class_level_defaults == []
    widened_methods = [
        node.name
        for node in mixin.body
        if isinstance(node, ast.FunctionDef)
        and node.args.args
        and node.args.args[0].annotation is not None
        and PROTOCOL_HOST_NAME in ast.unparse(node.args.args[0].annotation)
    ]
    assert "_normalize_mapping" in widened_methods

    # The Protocol host must declare the five host attributes.
    protocol = next(
        node
        for node in contract_tree.body
        if isinstance(node, ast.ClassDef) and node.name == PROTOCOL_HOST_NAME
    )
    declared = {
        node.name for node in protocol.body if isinstance(node, ast.FunctionDef)
    }
    assert {
        "provider",
        "entity_type",
        "profile",
        "rule_set",
        "allow_compatibility_fallback",
    } <= declared


def test_issue_10596_record_normalization_processor_satisfies_protocol_at_runtime() -> (
    None
):
    from bioetl.application.core.record_normalization_processor import (
        RecordNormalizationProcessor,
    )

    processor = RecordNormalizationProcessor(provider="chembl", entity_type=None)
    normalized = processor.normalize_business_data({"name": "  Aspirin  ", "_x": 1})
    assert normalized["name"] == "Aspirin"
    assert normalized["_x"] == 1


def test_issue_10596_unjustified_budget_file_exists_and_is_shrink_only() -> None:
    assert BUDGET.exists()
    budget = yaml.safe_load(BUDGET.read_text(encoding="utf-8"))
    assert budget["linked_issue"] == "#10596"
    assert budget["ratchet_policy"] == "shrink_only"
    assert isinstance(budget["max_unjustified_count"], int)
    census = _load_json(CENSUS_JSON)
    assert census["summary"]["unjustified_count"] <= budget["max_unjustified_count"]
