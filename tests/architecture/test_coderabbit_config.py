"""Validate the reviewed CodeRabbit file and its exact CI applicability route.

Schema snapshot: https://coderabbit.ai/integrations/schema.v2.json (2026-10-16).
SHA256: 7192851996cbbf9f328c1618e750572059d3bee979d69cf21a84c9ff29c53f6d.
Update from the official source and revalidate when adopting new vendor fields.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from scripts.engineering.ci.pr_gate import classify_changes, load_catalog
from scripts.engineering.ci.pr_lane_results import affected_pytest_targets

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "tests/fixtures/contracts/coderabbit-schema.v2.json"
TARGET = "tests/architecture/test_coderabbit_config.py"


class _UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate keys before schema validation can lose configuration."""

    def construct_mapping(
        self, node: yaml.MappingNode, deep: bool = False
    ) -> dict[object, object]:
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key: {key!r}",
                    key_node.start_mark,
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def test_coderabbit_configuration_matches_official_schema() -> None:
    """Use a pinned official schema offline, independent of vendor availability."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    config = yaml.load(
        (ROOT / ".coderabbit.yaml").read_text(encoding="utf-8"),
        Loader=_UniqueKeyLoader,
    )
    jsonschema.validate(config, schema)
    assert config["language"] == "ru-RU"
    assert config["reviews"]["path_filters"] == ["**"]
    for tool in (
        "ruff",
        "gitleaks",
        "shellcheck",
        "yamllint",
        "actionlint",
        "github-checks",
    ):
        assert config["reviews"]["tools"][tool]["enabled"] is True


@pytest.mark.parametrize(
    "document",
    [
        "reviews: {}\nreviews: {}\n",
        "reviews:\n  auto_review: {}\n  auto_review: {}\n",
        "reviews:\n  path_instructions:\n    - path: '**'\n      path: 'src/**'\n",
    ],
)
def test_config_loader_rejects_duplicate_keys(document: str) -> None:
    """Reject duplicates at the root, in nested mappings, and inside sequences."""
    with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key"):
        yaml.load(document, Loader=_UniqueKeyLoader)


def test_schema_rejects_invalid_review_controls() -> None:
    """Wrong types and out-of-range controls cannot qualify a config review."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for value in (-1, "3"):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {
                    "reviews": {
                        "auto_review": {"auto_pause_after_reviewed_commits": value}
                    }
                },
                schema,
            )


def test_reviewer_config_requires_real_validation() -> None:
    """A config-only diff must select this schema test, not an empty test lane."""
    catalog = load_catalog(ROOT / "configs/quality/github_required_checks.yaml")
    matrix = classify_changes(catalog, [".coderabbit.yaml"], head_sha="a" * 40)
    assert matrix["unclassified_files"] == []
    assert matrix["decisions"]["tests"] == {
        "decision": "required",
        "reason": "path_match",
    }
    assert affected_pytest_targets([".coderabbit.yaml"], repo_root=ROOT) == [TARGET]
    assert affected_pytest_targets(
        ["tests/fixtures/contracts/coderabbit-schema.v2.json"], repo_root=ROOT
    ) == [TARGET]


def test_unknown_root_yaml_still_fails_closed() -> None:
    """Only the named reviewer config is classified; arbitrary YAML stays unknown."""
    catalog = load_catalog(ROOT / "configs/quality/github_required_checks.yaml")
    matrix = classify_changes(catalog, [".unknown-reviewer.yaml"], head_sha="a" * 40)
    assert matrix["unclassified_files"] == [".unknown-reviewer.yaml"]
    assert all(item["decision"] == "required" for item in matrix["decisions"].values())
    assert affected_pytest_targets([".unknown-reviewer.yaml"], repo_root=ROOT) == []


def test_missing_reviewer_contract_fails_closed(tmp_path: Path) -> None:
    """A deleted contract must fail target selection rather than skip validation."""
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets([".coderabbit.yaml"], repo_root=tmp_path)
