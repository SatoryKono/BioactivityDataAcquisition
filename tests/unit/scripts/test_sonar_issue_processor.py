from __future__ import annotations

from pathlib import Path

from scripts.ai import check_sonar_issues as sonar_check
from scripts.ai import sonar_issue_processor as processor

SONAR_CONFIG_FILE = "sonar-project.properties"
SONAR_URL = "https://sonarcloud.io"
SONAR_PROJECT_KEY = "SatoryKono_BioactivityDataAcquisition"
SONAR_TOKEN_ENV = "SONARQUBE_TOKEN"
SUPPORTED_SCOPE_PATH = "src/bioetl/domain/file.py"
SUPPORTED_SCOPE_COMPONENT = f"repo:{SUPPORTED_SCOPE_PATH}"
SUPPORTED_SCOPE_TOTAL = "supported_scope_total"
SUPPORTED_NON_QUARANTINED_TOTAL = "supported_non_quarantined_total"
SUPPORTED_QUARANTINED_TOTAL = "supported_quarantined_total"
OUT_OF_SCOPE_TOTAL = "out_of_scope_total"
MATCHES_CURRENT_QUARANTINE = "matches_current_quarantine"
HISTORICAL_NEAR_ZERO_STATUS_IS_STALE = "historical_near_zero_status_is_stale"
LIVE_SCOPE_DRIFT_DETECTED = "live_scope_drift_detected"
LIVE_QUARANTINE_DRIFT_DETECTED = "live_quarantine_drift_detected"
DEFAULT_QUARANTINE_RATCHET_LIMIT = 159


def test_parse_java_properties_handles_multiline_exclusions() -> None:
    text = """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.sources=src/bioetl
sonar.exclusions=\\
  src/bioetl/application/services/foo.py,\\
  src/bioetl/application/core/bar.py
""".strip()

    properties = processor.parse_java_properties(text)

    assert properties["sonar.projectKey"] == SONAR_PROJECT_KEY
    assert properties["sonar.sources"] == "src/bioetl"
    assert properties["sonar.exclusions"] == (
        "src/bioetl/application/services/foo.py,src/bioetl/application/core/bar.py"
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


def test_build_wave_breakdown_maps_quarantine_entries_to_program_waves() -> None:
    breakdown = processor.build_wave_breakdown(
        [
            "src/bioetl/application/services/a.py",
            "src/bioetl/interfaces/cli/command.py",
            "src/bioetl/infrastructure/config/runtime.py",
            "src/bioetl/domain/filtering/input_config.py",
        ]
    )

    wave_counts = {
        wave["issue_number"]: wave["entry_count"] for wave in breakdown["waves"]
    }

    assert wave_counts[3106] == 1
    assert wave_counts[3107] == 1
    assert wave_counts[3108] == 1
    assert wave_counts[3109] == 1
    assert breakdown["mapped_entry_count"] == 4
    assert breakdown["unmapped_entry_count"] == 0
    assert breakdown["residual"]["entries"] == []


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
    config = tmp_path / SONAR_CONFIG_FILE
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
        sonar_url=SONAR_URL,
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
    assert report["assessment"][HISTORICAL_NEAR_ZERO_STATUS_IS_STALE] is True
    assert report["assessment"]["live_measurement_ready"] is False
    assert report["assessment"]["quarantine_ratchet_limit"] == (
        DEFAULT_QUARANTINE_RATCHET_LIMIT
    )
    assert report["assessment"]["quarantine_ratchet_remaining"] == (
        DEFAULT_QUARANTINE_RATCHET_LIMIT - 2
    )
    assert report["program"]["umbrella_issue_number"] == 3104
    assert report["program"]["ratchet_issue_number"] == 3110
    wave_counts = {
        wave["issue_number"]: wave["entry_count"]
        for wave in report["program"]["wave_breakdown"]["waves"]
    }
    assert wave_counts[3106] == 2
    assert report["program"]["wave_breakdown"]["unmapped_entry_count"] == 0


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
        sonar_url=SONAR_URL,
        project_key=SONAR_PROJECT_KEY,
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
                        "component": SUPPORTED_SCOPE_COMPONENT,
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
        sonar_url=SONAR_URL,
        project_key=SONAR_PROJECT_KEY,
        token="good-token",
        supported_sources=["src/bioetl"],
        quarantine_patterns=[SUPPORTED_SCOPE_PATH],
    )

    assert summary["status"] == "ok"
    assert summary[SUPPORTED_SCOPE_TOTAL] == 1
    assert summary[SUPPORTED_NON_QUARANTINED_TOTAL] == 0
    assert summary[SUPPORTED_QUARANTINED_TOTAL] == 1
    assert summary[OUT_OF_SCOPE_TOTAL] == 1
    assert summary["supported_scope_buckets"] == [
        {"path_prefix": SUPPORTED_SCOPE_PATH, "count": 1}
    ]
    assert summary["supported_quarantined_buckets"] == [
        {"path_prefix": SUPPORTED_SCOPE_PATH, "count": 1}
    ]
    assert summary["out_of_scope_buckets"] == [
        {"path_prefix": "scripts/check.py", "count": 1}
    ]
    assert summary["issues"][0]["in_supported_scope"] is True
    assert summary["issues"][0][MATCHES_CURRENT_QUARANTINE] is True
    assert summary["issues"][1]["in_supported_scope"] is False
    assert summary["issues"][1][MATCHES_CURRENT_QUARANTINE] is False


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
                        "component": SUPPORTED_SCOPE_COMPONENT,
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
        sonar_url=SONAR_URL,
        project_key=SONAR_PROJECT_KEY,
        token="good-token",
        supported_sources=["src/bioetl"],
        quarantine_patterns=["src/bioetl/other.py"],
    )

    assert summary["status"] == "ok"
    assert summary[SUPPORTED_SCOPE_TOTAL] == 1
    assert summary[SUPPORTED_NON_QUARANTINED_TOTAL] == 1
    assert summary[SUPPORTED_QUARANTINED_TOTAL] == 0
    assert summary["supported_scope_buckets"] == [
        {"path_prefix": SUPPORTED_SCOPE_PATH, "count": 1}
    ]
    assert summary["supported_non_quarantined_buckets"] == [
        {"path_prefix": SUPPORTED_SCOPE_PATH, "count": 1}
    ]
    assert summary["out_of_scope_buckets"] == []


def test_fetch_live_issue_summary_aggregates_multiple_pages(monkeypatch) -> None:
    class _Response:
        status_code = 200

        def __init__(self, issues: list[dict[str, object]], total: int) -> None:
            self._issues = issues
            self._total = total

        def json(self) -> dict[str, object]:
            return {
                "paging": {"total": self._total, "pageSize": 100},
                "facets": [
                    {
                        "property": "severities",
                        "values": [{"val": "MAJOR", "count": 1}],
                    },
                    {
                        "property": "types",
                        "values": [{"val": "CODE_SMELL", "count": 1}],
                    },
                ],
                "issues": self._issues,
            }

    def _fake_get(*args, **kwargs):  # type: ignore[no-untyped-def]
        page = kwargs["params"]["p"]
        if page == 1:
            return _Response(
                issues=[
                    {
                        "key": "one",
                        "component": SUPPORTED_SCOPE_COMPONENT,
                        "rule": "python:S1",
                        "severity": "MAJOR",
                        "message": "page 1 first issue",
                        "line": 11,
                    },
                ],
                total=3,
            )
        if page == 2:
            return _Response(
                issues=[
                    {
                        "key": "two",
                        "component": "repo:scripts/check.py",
                        "rule": "python:S2",
                        "severity": "CRITICAL",
                        "message": "page 1 second issue",
                        "line": 22,
                    },
                    {
                        "key": "three",
                        "component": SUPPORTED_SCOPE_COMPONENT,
                        "rule": "python:S3",
                        "severity": "MINOR",
                        "message": "page 1 third issue",
                        "line": 33,
                    },
                ],
                total=3,
            )

        raise AssertionError(f"unexpected page {page}")

    monkeypatch.setattr(processor.requests, "get", _fake_get)

    summary = processor.fetch_live_issue_summary(
        sonar_url=SONAR_URL,
        project_key=SONAR_PROJECT_KEY,
        token="good-token",
        supported_sources=["src/bioetl"],
        quarantine_patterns=[],
    )

    assert summary["status"] == "ok"
    assert summary["total"] == 3
    assert summary[SUPPORTED_SCOPE_TOTAL] == 2
    assert summary["out_of_scope_total"] == 1
    assert [issue["key"] for issue in summary["issues"]] == ["one", "two", "three"]
    assert summary["issues"][0][MATCHES_CURRENT_QUARANTINE] is False


def test_build_baseline_report_marks_quarantine_drift_when_live_issue_hits_exclusion(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / SONAR_CONFIG_FILE
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
                        "component": SUPPORTED_SCOPE_COMPONENT,
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
        sonar_url=SONAR_URL,
        token="good-token",
    )

    assert report["assessment"]["live_measurement_ready"] is True
    assert report["assessment"][LIVE_SCOPE_DRIFT_DETECTED] is False
    assert report["assessment"][LIVE_QUARANTINE_DRIFT_DETECTED] is True
    assert report["assessment"]["live_authoritative_scope_ready"] is False
    assert report["assessment"]["live_supported_scope_issue_count"] == 1
    assert report["assessment"]["live_supported_non_quarantined_issue_count"] == 0
    assert report["assessment"]["live_supported_quarantined_issue_count"] == 1


def test_check_sonar_issues_strict_live_fails_when_live_measurement_missing(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / SONAR_CONFIG_FILE
    config.write_text(
        """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.sources=src/bioetl
sonar.exclusions=src/bioetl/application/services/a.py
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(SONAR_TOKEN_ENV, raising=False)

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
    config = tmp_path / SONAR_CONFIG_FILE
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
    monkeypatch.delenv(SONAR_TOKEN_ENV, raising=False)

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
    config = tmp_path / SONAR_CONFIG_FILE
    config.write_text(
        """
sonar.projectKey=SatoryKono_BioactivityDataAcquisition
sonar.sources=src/bioetl
sonar.exclusions=src/bioetl/application/services/a.py
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(SONAR_TOKEN_ENV, raising=False)

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
    config.write_text(f"sonar.projectKey={SONAR_PROJECT_KEY}\n", encoding="utf-8")

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
                SUPPORTED_SCOPE_TOTAL: 1,
                SUPPORTED_NON_QUARANTINED_TOTAL: 0,
                SUPPORTED_QUARANTINED_TOTAL: 1,
                OUT_OF_SCOPE_TOTAL: 0,
            },
            "assessment": {
                HISTORICAL_NEAR_ZERO_STATUS_IS_STALE: False,
                LIVE_SCOPE_DRIFT_DETECTED: False,
                LIVE_QUARANTINE_DRIFT_DETECTED: True,
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
    config.write_text(f"sonar.projectKey={SONAR_PROJECT_KEY}\n", encoding="utf-8")

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
                SUPPORTED_SCOPE_TOTAL: 0,
                SUPPORTED_NON_QUARANTINED_TOTAL: 0,
                SUPPORTED_QUARANTINED_TOTAL: 0,
                OUT_OF_SCOPE_TOTAL: 0,
            },
            "assessment": {
                HISTORICAL_NEAR_ZERO_STATUS_IS_STALE: False,
                LIVE_SCOPE_DRIFT_DETECTED: False,
                LIVE_QUARANTINE_DRIFT_DETECTED: False,
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
