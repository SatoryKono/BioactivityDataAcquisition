"""Behavior tests for one-line interface coverage residuals in #10469."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.interfaces.cli.commands import export as export_command
from bioetl.interfaces.http.selected_run_status import _load_report_assessment


pytestmark = pytest.mark.unit


def test_export_command_scrubs_helper_binding_from_package_root() -> None:
    package = type("Package", (), {})()
    package.export_support = object()

    with patch.object(
        export_command,
        "sys",
        type("Sys", (), {"modules": {export_command.__package__: package}})(),
    ):
        export_command._scrub_helper_module_binding()

    assert not hasattr(package, "export_support")


def test_selected_run_report_rejects_non_mapping_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "pipeline_run_report_v2",
                "identity": {
                    "run_id": "run-1",
                    "pipeline_name": "chembl_activity",
                },
                "selected_run_snapshot": "corrupt",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="snapshot_corrupt"):
        _load_report_assessment(path, "chembl_activity", "run-1")
