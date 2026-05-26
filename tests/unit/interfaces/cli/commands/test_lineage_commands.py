"""Unit tests for lineage CLI commands."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from click.testing import CliRunner

from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageFragmentInspectionResult,
    LineageNodeRelationResult,
    LineageRunExplanationResult,
    LineageTraceResult,
)
from bioetl.domain.lineage import (
    DatasetRef,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.interfaces.cli.main import cli


class _FakeLineageService:
    def __init__(self) -> None:
        self._dataset_node = DatasetRef(
            layer="silver",
            logical_name="chembl.activity",
            version=12,
        ).to_node_ref()
        self._upstream_node = LineageNodeRef(
            node_type=LineageNodeType.BRONZE_BATCH,
            node_id="bronze_batch:batch-1",
        )
        self._fragment = LineageGraphFragment(
            fragment_id="silver:fragment-1",
            stored_fragment_id="silver:fragment-1:occurrence:abc123",
            nodes=(self._dataset_node, self._upstream_node),
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

    def show_fragment(
        self, fragment_id: str, semantic: bool = False
    ) -> LineageFragmentInspectionResult:
        if fragment_id == "missing":
            raise ValueError("missing")
        return LineageFragmentInspectionResult(fragment=self._fragment)

    def trace(self, dataset_ref: str) -> LineageTraceResult:
        if dataset_ref == "missing":
            raise ValueError("missing")
        return LineageTraceResult(
            dataset_ref=dataset_ref,
            fragment_ids=("silver:fragment-1",),
            stored_fragment_ids=("silver:fragment-1:occurrence:abc123",),
            upstream=(
                LineageNodeRelationResult(
                    fragment_id="silver:fragment-1",
                    stored_fragment_id="silver:fragment-1:occurrence:abc123",
                    edge_type="derived_from",
                    node=self._upstream_node,
                ),
            ),
        )

    def explain_run(self, identifier: str) -> LineageRunExplanationResult:
        if identifier == "missing":
            raise ValueError("missing")
        return LineageRunExplanationResult(
            identifier=identifier,
            run_id="00000000-0000-0000-0000-000000000001",
            manifest_id="manifest-1",
            fragment_ids=("silver:fragment-1",),
            stored_fragment_ids=("silver:fragment-1:occurrence:abc123",),
            produced_datasets=(self._dataset_node,),
            source_systems=(
                LineageNodeRef(
                    node_type=LineageNodeType.SOURCE_SYSTEM,
                    node_id="source_system:chembl",
                    label="chembl",
                ),
            ),
        )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def _patch_lineage_service(monkeypatch: Any, service: object) -> None:
    import bioetl.interfaces.cli.commands.lineage as lineage_cmd

    monkeypatch.setattr(
        lineage_cmd,
        "get_lineage_service",
        lambda: service,
        raising=True,
    )


@pytest.mark.unit
class TestLineageCommands:
    def test_lineage_help_shows_subcommands(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(cli, ["lineage", "--help"])

        assert result.exit_code == 0
        assert "trace" in result.output
        assert "explain" in result.output
        assert "show-fragment" in result.output

    def test_trace_json_outputs_relations(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_lineage_service(monkeypatch, _FakeLineageService())

        result = cli_runner.invoke(
            cli,
            [
                "lineage",
                "trace",
                "--dataset-ref",
                "silver:chembl.activity@12",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["dataset_ref"] == "silver:chembl.activity@12"
        assert payload["stored_fragment_ids"] == ["silver:fragment-1:occurrence:abc123"]
        assert payload["upstream"][0]["node"]["node_id"] == "bronze_batch:batch-1"
        assert payload["upstream"][0]["stored_fragment_id"] == (
            "silver:fragment-1:occurrence:abc123"
        )

    def test_explain_defaults_to_text_output(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_lineage_service(monkeypatch, _FakeLineageService())

        result = cli_runner.invoke(
            cli,
            ["lineage", "explain", "--manifest-id", "manifest-1"],
        )

        assert result.exit_code == 0
        assert "Lineage Run" in result.output
        assert "manifest_id: manifest-1" in result.output
        assert "stored_fragments: 1" in result.output
        assert "Produced Datasets" in result.output

    def test_show_fragment_json_outputs_fragment(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_lineage_service(monkeypatch, _FakeLineageService())

        result = cli_runner.invoke(
            cli,
            ["lineage", "show-fragment", "silver:fragment-1", "--format", "json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["fragment"]["fragment_id"] == "silver:fragment-1"
        assert payload["fragment"]["stored_fragment_id"] == (
            "silver:fragment-1:occurrence:abc123"
        )

    def test_explain_requires_exactly_one_identifier(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_lineage_service(monkeypatch, _FakeLineageService())

        result = cli_runner.invoke(
            cli,
            [
                "lineage",
                "explain",
                "--run-id",
                "run-1",
                "--manifest-id",
                "manifest-1",
            ],
        )

        assert result.exit_code == 0
        assert "Provide exactly one of --run-id or --manifest-id" in result.stderr
