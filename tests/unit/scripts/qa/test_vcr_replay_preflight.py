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
"""Unit tests for VCR replay preflight checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa.vcr import check_replay_preflight as preflight

pytestmark = pytest.mark.unit


def _write_catalog(root: Path, *, cassette_count: int, metadata_count: int) -> Path:
    catalog = root / "reports" / "quality" / "vcr-metadata-catalog.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        json.dumps(
            {
                "totals": {
                    "cassette_count": cassette_count,
                    "metadata_sidecar_count": metadata_count,
                    "unowned_cassette_count": 0,
                    "duplicate_scenario_stem_count": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    return catalog


def test_collect_vcr_replay_preflight_reports_exact_lfs_pointer_paths(
    tmp_path: Path,
) -> None:
    cassette_dir = tmp_path / "tests" / "fixtures" / "vcr" / "chembl"
    cassette_dir.mkdir(parents=True)
    pointer = cassette_dir / "provider_contract_case.yaml"
    pointer.write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123\n",
        encoding="utf-8",
    )
    (cassette_dir / "provider_contract_case_meta.yaml").write_text(
        "managed_inventory: true\n",
        encoding="utf-8",
    )
    _write_catalog(tmp_path, cassette_count=1, metadata_count=1)

    report = preflight.collect_vcr_replay_preflight(tmp_path)

    assert report["unresolved_lfs_pointers"] == [
        {
            "path": "tests/fixtures/vcr/chembl/provider_contract_case.yaml",
            "strict_replay_blocked": True,
        }
    ]
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "unresolved_vcr_lfs_pointers" in blocker_ids
    assert "unresolved_replay_critical_lfs_pointers" in blocker_ids
    assert "git lfs pull" in report["remediation"]


def test_collect_vcr_replay_preflight_accepts_clean_catalog_and_secret_filter(
    tmp_path: Path,
) -> None:
    cassette_dir = tmp_path / "tests" / "fixtures" / "vcr" / "pubchem"
    cassette_dir.mkdir(parents=True)
    (cassette_dir / "test_health.yaml").write_text(
        "interactions: []\n", encoding="utf-8"
    )
    (cassette_dir / "test_health_meta.yaml").write_text(
        "managed_inventory: true\n",
        encoding="utf-8",
    )
    _write_catalog(tmp_path, cassette_count=1, metadata_count=1)

    report = preflight.collect_vcr_replay_preflight(tmp_path)

    assert report["blockers"] == []
    assert report["catalog"]["totals_match"] is True
    assert report["sanitizer_status"]["replay_only"] is True
    assert report["sanitizer_status"]["has_request_sanitizer"] is True


def test_main_strict_returns_nonzero_for_replay_blockers(tmp_path: Path) -> None:
    cassette_dir = tmp_path / "tests" / "fixtures" / "vcr" / "chembl"
    cassette_dir.mkdir(parents=True)
    (cassette_dir / "test_chembl_activity_full_run.yaml").write_text(
        "version https://git-lfs.github.com/spec/v1\n",
        encoding="utf-8",
    )

    assert preflight.main(["--root", str(tmp_path), "--strict"]) == 1


def test_main_prints_only_allowlisted_public_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sentinel = "DO-NOT-PRINT-SECRET"
    absolute_path = f"C:/Users/private/{sentinel}"
    internal_report = {
        "schema_version": "vcr-replay-preflight-v1",
        "root": absolute_path,
        "vcr_root": "tests/fixtures/vcr",
        "cassette_count": 1,
        "metadata_sidecar_count": 0,
        "unresolved_lfs_pointers": [
            {
                "path": absolute_path,
                "strict_replay_blocked": True,
                "headers": {"authorization": sentinel},
                "query": sentinel,
                "payload": sentinel,
                "callback": sentinel,
            }
        ],
        "strict_unresolved_lfs_pointer_count": 1,
        "catalog": {"path": "reports/quality/vcr-metadata-catalog.json"},
        "sanitizer_status": {
            "record_mode": "none",
            "replay_only": True,
            "has_request_sanitizer": True,
            "has_response_filter": True,
            "unknown": sentinel,
        },
        "blockers": [
            {
                "id": "unresolved_vcr_lfs_pointers",
                "message": sentinel,
                "paths": [absolute_path],
            },
            {"id": sentinel, "message": sentinel},
        ],
        "unknown": {"nested": sentinel},
    }
    monkeypatch.setattr(
        preflight,
        "collect_vcr_replay_preflight",
        lambda *args, **kwargs: internal_report,
    )

    assert preflight.main([]) == 0

    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    assert sentinel not in stdout
    assert "root" not in payload
    assert payload["schema_version"] == "vcr-replay-preflight-public-v2"
    assert payload["blockers"] == [{"id": "unresolved_vcr_lfs_pointers"}]
