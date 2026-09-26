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
"""Assert-density policy for table-driven unit suites (#6646)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_POLICY = _REPO / "configs/quality/unit_assert_density_policy.yaml"
_S2_SCHEMA_MODULE = (
    "tests/unit/domain/schemas/semanticscholar/test_publication_schema.py"
)


def test_unit_assert_density_policy_reviews_known_low_ratio_modules() -> None:
    payload = yaml.safe_load(_POLICY.read_text(encoding="utf-8"))
    assert payload["policy"]["forbid_empty_test_bodies"] is True
    assert payload["policy"]["require_schema_reference_in_schema_modules"] is True
    reviewed = payload["reviewed_modules"]
    assert isinstance(reviewed, list) and reviewed
    paths = {str(row["path"]) for row in reviewed}
    assert _S2_SCHEMA_MODULE in paths
    for row in reviewed:
        path = _REPO / row["path"]
        assert path.is_file(), f"missing reviewed module {row['path']}"
        assert row["classification"] in {
            "table_driven_parametrized",
            "schema_validation_parametrized",
            "metrics_side_effect_spy",
        }


def test_semanticscholar_publication_schema_suite_exercises_owner_schema() -> None:
    """C1-TS-001: no bare-pass / no self-fulfilled regex-only suite."""
    path = _REPO / _S2_SCHEMA_MODULE
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "SemanticScholarPublicationSchema" in source
    assert "assert_schema_validates_frame" in source or ".validate(" in source

    empty_pass_tests: list[str] = []
    schema_touching = 0
    test_functions = 0
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            members = node.body
            class_name = node.name
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            members = [node]
            class_name = ""
        else:
            continue
        for item in members:
            if not isinstance(item, ast.FunctionDef):
                continue
            if not item.name.startswith("test_"):
                continue
            test_functions += 1
            body = [stmt for stmt in item.body if not isinstance(stmt, ast.Expr)]
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                empty_pass_tests.append(f"{class_name}.{item.name}")
            item_src = ast.get_source_segment(source, item) or ""
            if (
                "SemanticScholarPublicationSchema" in item_src
                or "assert_schema_validates_frame" in item_src
            ):
                schema_touching += 1

    assert not empty_pass_tests, f"empty pass-only tests: {empty_pass_tests}"
    assert test_functions >= 20
    assert schema_touching >= int(test_functions * 0.7), (
        f"only {schema_touching}/{test_functions} tests reference "
        "SemanticScholarPublicationSchema / assert_schema_validates_frame"
    )
