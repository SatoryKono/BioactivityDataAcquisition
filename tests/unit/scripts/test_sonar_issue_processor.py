from __future__ import annotations

from pathlib import Path

from scripts.ai import check_sonar_issues as sonar_check
from scripts.ai import sonar_issue_processor as processor


def test_parse_java_properties_handles_multiline_exclusions() -> None:
    text = """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.sources=src/bioetl
sonar.exclusions=\\
  src/bioetl/application/services/foo.py,\\
  src/bioetl/application/core/bar.py
""".strip()

    properties = processor.parse_java_properties(text)

    assert properties["sonar.projectKey"] == "SatoryKono_BioactivityDataAcquisition"
    assert properties["sonar.sources"] == "src/bioetl"
    assert properties["sonar.exclusions"] == (
        "src/bioetl/application/services/foo.py,"
        "src/bioetl/application/core/bar.py"
    )


def test_bucket_exclusions_groups_by_bioetl_family() -> None:
    buckets = processor.bucket_exclusions(
        [
            "src/bioetl/application/services/a.py",
            "src/bioetl/application/services/b.py",
            "src/bioetl/infrastructure/storage/c.py",
        ]
    )

    assert buckets[0] == {
        "path_prefix": "src/bioetl/application/services",
        "count": 2,
    }
    assert buckets[1] == {
        "path_prefix": "src/bioetl/infrastructure/storage",
        "count": 1,
    }


def test_bucket_issue_paths_groups_live_issues_by_family() -> None:
    buckets = processor.bucket_issue_paths(
        [
            {"path": "src/bioetl/application/services/a.py"},
            {"path": "src/bioetl/application/services/b.py"},
            {"path": "scripts/ai/check_sonar_issues.py"},
        ]
    )

    assert buckets[0] == {
        "path_prefix": "src/bioetl/application/services",
        "count": 2,
    }
    assert buckets[1] == {
        "path_prefix": "scripts/ai/check_sonar_issues.py",
        "count": 1,
    }


def test_parse_sources_splits_and_normalizes_roots() -> None:
    sources = processor.parse_sources("src/bioetl, scripts/, docs ")

    assert sources == ["src/bioetl", "scripts", "docs"]


def test_is_in_supported_scope_checks_prefix_boundaries() -> None:
    assert processor._is_in_supported_scope("src/bioetl/domain/a.py", ["src/bioetl"])
    assert not processor._is_in_supported_scope(
        "scripts/check.py",
        ["src/bioetl"],
    )


def test_matches_current_quarantine_supports_exact_and_glob_patterns() -> None:
    assert processor._matches_current_quarantine(
        "src/bioetl/domain/a.py",
        ["src/bioetl/domain/a.py"],
    )
    assert processor._matches_current_quarantine(
        "src/bioetl/domain/nested/a.py",
        ["src/bioetl/domain/**"],
    )
    assert not processor._matches_current_quarantine(
        "src/bioetl/application/a.py",
        ["src/bioetl/domain/**"],
    )


def test_build_baseline_report_marks_historical_status_stale_when_quarantine_exists(
    tmp_path: Path,
) -> None:
    config = tmp_path / "sonar-project.properties"
    config.write_text(
        """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.organization=satorykono
sonar.sources=src/bioetl
sonar.exclusions=\\
  src/bioetl/application/services/a.py,\\
  src/bioetl/application/composite/b.py
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = processor.build_baseline_report(
        config_path=config,
        sonar_url="https://sonarcloud.io",
        token=None,
    )

    assert report["quarantine"]["entry_count"] == 2
    assert report["quarantine"]["entries"] == [
        "src/bioetl/application/services/a.py",
        "src/bioetl/application/composite/b.py",
    ]
    assert report["quarantine"]["buckets"] == [
        {
            "path_prefix": "src/bioetl/application/services",
            "count": 1,
        },
        {
            "path_prefix": "src/bioetl/application/composite",
            "count": 1,
        },
    ]
    assert report["live_issues"]["status"] == "skipped"
    assert report["assessment"]["historical_near_zero_status_is_stale"] is True
    assert report["assessment"]["live_measurement_ready"] is False


def test_fetch_live_issue_summary_reports_http_errors(monkeypatch) -> None:
    class _Response:
        status_code = 401
        text = "Unauthorized"

        def json(self) -> dict[str, object]:
            return {}

    def _fake_get(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _Response()

    monkeypatch.setattr(processor.requests, "get", _fake_get)

    summary = processor.fetch_live_issue_summary(
        sonar_url="https://sonarcloud.io",
        project_key="SatoryKono_BioactivityDataAcquisition",
        token="bad-token",
        supported_sources=["src/bioetl"],
        quarantine_patterns=[],
    )

    assert summary["status"] == "error"
    assert summary["reason"] == "http_error"
    assert summary["status_code"] == 401


def test_fetch_live_issue_summary_tracks_scope_drift(monkeypatch) -> None:
    class _Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "paging": {"total": 2, "pageSize": 100},
                "facets": [],
                "issues": [
                    {
                        "key": "one",
                        "component": "repo:src/bioetl/domain/file.py",
                        "rule": "python:S1",
                        "severity": "MAJOR",
                        "message": "supported",
                        "line": 10,
                    },
                    {
                        "key": "two",
                        "component": "repo:scripts/check.py",
                        "rule": "python:S2",
                        "severity": "CRITICAL",
                        "message": "drift",
                        "line": 20,
                    },
                ],
            }

    def _fake_get(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _Response()

    monkeypatch.setattr(processor.requests, "get", _fake_get)

    summary = processor.fetch_live_issue_summary(
        sonar_url="https://sonarcloud.io",
        project_key="SatoryKono_BioactivityDataAcquisition",
        token="good-token",
        supported_sources=["src/bioetl"],
        quarantine_patterns=["src/bioetl/domain/file.py"],
    )

    assert summary["status"] == "ok"
    assert summary["supported_scope_total"] == 1
    assert summary["supported_non_quarantined_total"] == 0
    assert summary["supported_quarantined_total"] == 1
    assert summary["out_of_scope_total"] == 1
    assert summary["supported_scope_buckets"] == [
        {"path_prefix": "src/bioetl/domain/file.py", "count": 1}
    ]
    assert summary["supported_quarantined_buckets"] == [
        {"path_prefix": "src/bioetl/domain/file.py", "count": 1}
    ]
    assert summary["out_of_scope_buckets"] == [
        {"path_prefix": "scripts/check.py", "count": 1}
    ]
    assert summary["issues"][0]["in_supported_scope"] is True
    assert summary["issues"][0]["matches_current_quarantine"] is True
    assert summary["issues"][1]["in_supported_scope"] is False
    assert summary["issues"][1]["matches_current_quarantine"] is False


def test_fetch_live_issue_summary_counts_active_supported_issues(monkeypatch) -> None:
    class _Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "paging": {"total": 1, "pageSize": 100},
                "facets": [],
                "issues": [
                    {
                        "key": "one",
                        "component": "repo:src/bioetl/domain/file.py",
                        "rule": "python:S1",
                        "severity": "MAJOR",
                        "message": "supported",
                        "line": 10,
                    }
                ],
            }

    def _fake_get(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _Response()

    monkeypatch.setattr(processor.requests, "get", _fake_get)

    summary = processor.fetch_live_issue_summary(
        sonar_url="https://sonarcloud.io",
        project_key="SatoryKono_BioactivityDataAcquisition",
        token="good-token",
        supported_sources=["src/bioetl"],
        quarantine_patterns=["src/bioetl/other.py"],
    )

    assert summary["status"] == "ok"
    assert summary["supported_scope_total"] == 1
    assert summary["supported_non_quarantined_total"] == 1
    assert summary["supported_quarantined_total"] == 0
    assert summary["supported_scope_buckets"] == [
        {"path_prefix": "src/bioetl/domain/file.py", "count": 1}
    ]
    assert summary["supported_non_quarantined_buckets"] == [
        {"path_prefix": "src/bioetl/domain/file.py", "count": 1}
    ]
    assert summary["out_of_scope_buckets"] == []
    assert summary["issues"][0]["matches_current_quarantine"] is False


def test_build_baseline_report_marks_quarantine_drift_when_live_issue_hits_exclusion(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / "sonar-project.properties"
    config.write_text(
        """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.organization=satorykono
sonar.sources=src/bioetl
sonar.exclusions=src/bioetl/domain/file.py
""".strip()
        + "\n",
        encoding="utf-8",
    )

    class _Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "paging": {"total": 1, "pageSize": 100},
                "facets": [],
                "issues": [
                    {
                        "key": "one",
                        "component": "repo:src/bioetl/domain/file.py",
                        "rule": "python:S1",
                        "severity": "MAJOR",
                        "message": "quarantined",
                        "line": 10,
                    }
                ],
            }

    def _fake_get(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _Response()

    monkeypatch.setattr(processor.requests, "get", _fake_get)

    report = processor.build_baseline_report(
        config_path=config,
        sonar_url="https://sonarcloud.io",
        token="good-token",
    )

    assert report["assessment"]["live_measurement_ready"] is True
    assert report["assessment"]["live_scope_drift_detected"] is False
    assert report["assessment"]["live_quarantine_drift_detected"] is True
    assert report["assessment"]["live_authoritative_scope_ready"] is False
    assert report["assessment"]["live_supported_scope_issue_count"] == 1
    assert report["assessment"]["live_supported_non_quarantined_issue_count"] == 0
    assert report["assessment"]["live_supported_quarantined_issue_count"] == 1


def test_check_sonar_issues_strict_live_fails_when_live_measurement_missing(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / "sonar-project.properties"
    config.write_text(
        """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.sources=src/bioetl
sonar.exclusions=src/bioetl/application/services/a.py
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SONARQUBE_TOKEN", raising=False)

    exit_code = sonar_check.main(
        [
            "--config",
            str(config),
            "--strict-live",
        ]
    )

    assert exit_code == 1


def test_check_sonar_issues_ratchet_fails_when_quarantine_grows(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / "sonar-project.properties"
    config.write_text(
        """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.sources=src/bioetl
sonar.exclusions=\\
  src/bioetl/application/services/a.py,\\
  src/bioetl/application/core/b.py
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SONARQUBE_TOKEN", raising=False)

    exit_code = sonar_check.main(
        [
            "--config",
            str(config),
            "--max-quarantine-entries",
            "1",
        ]
    )

    assert exit_code == 1


def test_check_sonar_issues_ratchet_passes_within_quarantine_limit(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / "sonar-project.properties"
    config.write_text(
        """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.sources=src/bioetl
sonar.exclusions=src/bioetl/application/services/a.py
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SONARQUBE_TOKEN", raising=False)

    exit_code = sonar_check.main(
        [
            "--config",
            str(config),
            "--max-quarantine-entries",
            "1",
        ]
    )

    assert exit_code == 0


def test_check_sonar_issues_authoritative_scope_flag_fails_on_drift(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / "sonar-project.properties"
    config.write_text(
        "sonar.projectKey=SatoryKono_BioactivityDataAcquisition\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sonar_check,
        "build_baseline_report",
        lambda **_kwargs: {
            "quarantine": {
                "config_path": str(config),
                "entry_count": 0,
                "top_buckets": [],
            },
            "live_issues": {
                "status": "ok",
                "total": 1,
                "supported_scope_total": 1,
                "supported_non_quarantined_total": 0,
                "supported_quarantined_total": 1,
                "out_of_scope_total": 0,
            },
            "assessment": {
                "historical_near_zero_status_is_stale": False,
                "live_scope_drift_detected": False,
                "live_quarantine_drift_detected": True,
            },
        },
    )

    exit_code = sonar_check.main(
        [
            "--config",
            str(config),
            "--strict-live",
            "--require-authoritative-scope",
        ]
    )

    assert exit_code == 1


def test_check_sonar_issues_authoritative_scope_flag_passes_without_drift(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / "sonar-project.properties"
    config.write_text(
        "sonar.projectKey=SatoryKono_BioactivityDataAcquisition\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sonar_check,
        "build_baseline_report",
        lambda **_kwargs: {
            "quarantine": {
                "config_path": str(config),
                "entry_count": 0,
                "top_buckets": [],
            },
            "live_issues": {
                "status": "ok",
                "total": 0,
                "supported_scope_total": 0,
                "supported_non_quarantined_total": 0,
                "supported_quarantined_total": 0,
                "out_of_scope_total": 0,
            },
            "assessment": {
                "historical_near_zero_status_is_stale": False,
                "live_scope_drift_detected": False,
                "live_quarantine_drift_detected": False,
            },
        },
    )

    exit_code = sonar_check.main(
        [
            "--config",
            str(config),
            "--strict-live",
            "--require-authoritative-scope",
        ]
    )

    assert exit_code == 0
