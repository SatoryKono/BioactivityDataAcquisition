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
"""Manifest checks for tracked non-ChEMBL edge-case Bronze fixtures."""

from __future__ import annotations

import pytest

import json
from pathlib import Path

import yaml

pytestmark = pytest.mark.integration

MANIFEST_PATH = Path("configs/base/bronze_fixture_manifest.yaml")
EDGE_PIPELINES = {
    "crossref/publication",
    "openalex/publication",
    "pubchem/compound",
    "pubmed/publication",
    "semanticscholar/publication",
    "uniprot/idmapping",
    "uniprot/protein",
}


def test_non_chembl_edge_fixture_manifest_entries_are_present_and_valid() -> None:
    payload = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    fixtures = payload["fixtures"]

    for key in EDGE_PIPELINES:
        entry = fixtures[key]
        edge_entries = entry["edge_fixtures"]
        assert isinstance(edge_entries, list)
        assert edge_entries
        for edge_entry in edge_entries:
            assert edge_entry["fixture_kind"] == "tracked_edge_case_sample"
            fixture_path = Path(edge_entry["fixture_path"])
            assert fixture_path.exists()
            lines = [
                line
                for line in fixture_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(lines) == edge_entry["records"]
            for line in lines:
                assert isinstance(json.loads(line), dict)
