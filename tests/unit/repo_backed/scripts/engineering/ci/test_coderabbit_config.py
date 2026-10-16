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

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[6]
SCHEMA = ROOT / "tests/fixtures/contracts/coderabbit-schema.v2.json"
TARGET = "tests/unit/repo_backed/scripts/engineering/ci/test_coderabbit_config.py"


def test_coderabbit_configuration_matches_official_schema() -> None:
    """Use a pinned official schema offline, independent of vendor availability."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    config = yaml.safe_load((ROOT / ".coderabbit.yaml").read_text(encoding="utf-8"))
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
