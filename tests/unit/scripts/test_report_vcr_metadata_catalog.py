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
"""Regression tests for the VCR metadata catalog generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa import report_vcr_metadata_catalog as module


pytestmark = pytest.mark.unit


def test_python_reference_scan_prefers_longest_overlapping_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    short_token = "test_overlap_case"
    long_token = "SyntheticAdapterIntegration.test_overlap_case"
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    (scan_root / "openalex_owner.py").write_text(
        f'CASSETTE = "{long_token}"\n',
        encoding="utf-8",
    )
    (scan_root / "pubmed_owner.py").write_text(
        f'CASSETTE = "{short_token}"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "REACHABILITY_SCAN_ROOTS", (Path("scan"),))

    owners = module._run_python_reference_scan(
        repo_root=tmp_path,
        tokens=[
            short_token,
            long_token,
        ],
    )

    assert owners[long_token] == {"scan/openalex_owner.py"}
    assert owners[short_token] == {"scan/pubmed_owner.py"}
