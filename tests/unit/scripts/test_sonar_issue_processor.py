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
    )

    assert summary["status"] == "error"
    assert summary["reason"] == "http_error"
    assert summary["status_code"] == 401


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
