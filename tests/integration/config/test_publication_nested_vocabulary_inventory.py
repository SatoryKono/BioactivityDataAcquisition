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
"""Governance checks for nested publication-sidecar vocabularies."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.qa.extract_publication_nested_vocab import (
    extract_publication_nested_vocab,
)

pytestmark = pytest.mark.integration

INVENTORY_PATH = Path("configs/vocab/publication_nested.yaml")


def test_publication_nested_inventory_covers_observed_fixture_values() -> None:
    payload = extract_publication_nested_vocab(
        openalex_paths=[
            Path(
                "tests/fixtures/bronze/openalex/publication/sample_ci_2026-04-29.jsonl"
            ),
            Path(
                "tests/fixtures/bronze/openalex/publication/sample_edge_nested_vocab_2026-05-05.jsonl"
            ),
        ],
        semanticscholar_paths=[
            Path(
                "tests/fixtures/bronze/semanticscholar/publication/sample_ci_2026-04-30.jsonl"
            ),
            Path(
                "tests/fixtures/bronze/semanticscholar/publication/sample_edge_publication_types_citations_2026-05-05.jsonl"
            ),
        ],
        pubmed_paths=[
            Path(
                "tests/fixtures/bronze/pubmed/publication/sample_edge_publication_types_mesh_2026-05-05.jsonl"
            )
        ],
    )
    inventory = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))

    for provider, fields in payload.items():
        for field_name, observed in fields.items():
            allowed = set(inventory["providers"][provider][field_name]["values"])
            assert set(observed) <= allowed, (
                f"Unclassified nested publication values for {provider}.{field_name}: "
                f"{sorted(set(observed) - allowed)}"
            )
