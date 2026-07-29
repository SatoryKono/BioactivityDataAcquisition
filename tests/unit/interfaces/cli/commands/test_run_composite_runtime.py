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
"""Unit tests for canonical run-composite runtime helper module.

Tests parse_enrich_only, build_runtime_config, and echo_composite_startup.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig
from bioetl.interfaces.cli.commands.domains.composite.runtime import (
    build_runtime_config,
    echo_composite_startup,
    parse_enrich_only,
)

pytestmark = pytest.mark.unit

CACHED_BRONZE_PATH = "test-output/bronze"


class TestParseEnrichOnly:
    """Tests for parse_enrich_only."""

    def test_parse_enrich_only__none_returns_none__1bab081f(self) -> None:
        """None input returns None."""
        assert parse_enrich_only(None) is None

    def test_parse_enrich_only__string_returns_none__f1fe953f(self) -> None:
        """Empty string input returns None."""
        assert parse_enrich_only("") is None

    def test_parse_enrich_only__single_value__3554e235(self) -> None:
        """Single enricher name returns single-element tuple."""
        result = parse_enrich_only("crossref")
        assert result == ("crossref",)

    def test_multiple_values(self) -> None:
        """Comma-separated names return tuple of stripped strings."""
        result = parse_enrich_only("crossref,pubmed")
        assert result == ("crossref", "pubmed")

    def test_values_with_spaces_are_stripped(self) -> None:
        """Whitespace around enricher names is stripped."""
        result = parse_enrich_only("crossref , pubmed , openalex")
        assert result == ("crossref", "pubmed", "openalex")


class TestBuildRuntimeConfig:
    """Tests for build_runtime_config."""

    def test_returns_composite_runtime_config(self) -> None:
        """Returns a CompositeRuntimeConfig instance."""
        result = build_runtime_config(
            resume=False,
            dry_run=False,
            seed_limit=None,
            enrich_only=None,
            required_only=False,
            force_enricher=None,
            use_cached_bronze=False,
            cached_bronze_date=None,
            cached_bronze_path=None,
            cached_bronze_enrichers=None,
            cached_bronze_dependencies=False,
        )
        assert isinstance(result, CompositeRuntimeConfig)

    def test_values_passed_through(self) -> None:
        """Config values are correctly set on the returned object."""
        result = build_runtime_config(
            resume=True,
            dry_run=True,
            seed_limit=50,
            enrich_only="crossref,pubmed",
            required_only=True,
            force_enricher="crossref",
            use_cached_bronze=True,
            cached_bronze_date="2026-01-01",
            cached_bronze_path=CACHED_BRONZE_PATH,
            cached_bronze_enrichers=False,
            cached_bronze_dependencies=True,
        )
        assert result.resume is True
        assert result.dry_run is True
        assert result.seed_limit == 50
        assert result.enrich_only == ("crossref", "pubmed")
        assert result.required_only is True
        assert result.force_enricher == "crossref"
        assert result.use_cached_bronze is True
        assert result.cached_bronze_date == "2026-01-01"
        assert result.cached_bronze_path == CACHED_BRONZE_PATH
        assert result.cached_bronze_enrichers is False
        assert result.cached_bronze_dependencies is True

    def test_enrich_only_none_maps_to_none(self) -> None:
        """enrich_only=None produces None on config."""
        result = build_runtime_config(
            resume=False,
            dry_run=False,
            seed_limit=None,
            enrich_only=None,
            required_only=False,
            force_enricher=None,
            use_cached_bronze=False,
            cached_bronze_date=None,
            cached_bronze_path=None,
            cached_bronze_enrichers=None,
            cached_bronze_dependencies=False,
        )
        assert result.enrich_only is None


class TestEchoCompositeStartup:
    """Tests for echo_composite_startup — covers lines 96-101."""

    def test_always_echoes_starting_message(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Starting message is always printed (line 96)."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ):
            echo_composite_startup(
                composite="publication",
                dry_run=False,
                resume=False,
                cached_bronze_enabled=False,
                health_server=False,
                health_port=8081,
            )

        out = capsys.readouterr().out
        assert "Starting composite pipeline: publication" in out

    def test_dry_run_true_echoes_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Dry-run warning is printed when dry_run=True (line 97-98)."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ):
            echo_composite_startup(
                composite="publication",
                dry_run=True,
                resume=False,
                cached_bronze_enabled=False,
                health_server=False,
                health_port=8081,
            )

        out = capsys.readouterr().out
        assert "Dry-run mode: no data will be written" in out

    def test_dry_run_false_no_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Dry-run warning is NOT printed when dry_run=False."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ):
            echo_composite_startup(
                composite="publication",
                dry_run=False,
                resume=False,
                cached_bronze_enabled=False,
                health_server=False,
                health_port=8081,
            )

        out = capsys.readouterr().out
        assert "Dry-run mode" not in out

    def test_resume_true_echoes_info(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Resume message is printed when resume=True (line 99-100)."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ):
            echo_composite_startup(
                composite="publication",
                dry_run=False,
                resume=True,
                cached_bronze_enabled=False,
                health_server=False,
                health_port=8081,
            )

        out = capsys.readouterr().out
        assert "Resume mode: continuing from last checkpoint" in out

    def test_resume_false_no_info(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Resume message is NOT printed when resume=False."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ):
            echo_composite_startup(
                composite="publication",
                dry_run=False,
                resume=False,
                cached_bronze_enabled=False,
                health_server=False,
                health_port=8081,
            )

        out = capsys.readouterr().out
        assert "Resume mode" not in out

    def test_calls_echo_health_server_info(self) -> None:
        """echo_health_server_info is called with correct args (line 101)."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ) as mock_echo:
            echo_composite_startup(
                composite="publication",
                dry_run=False,
                resume=False,
                cached_bronze_enabled=False,
                health_server=True,
                health_port=9090,
            )

        mock_echo.assert_called_once_with(True, 9090)

    def test_combined_dry_run_and_resume(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Both dry-run warning and resume message appear when both flags are True."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ):
            echo_composite_startup(
                composite="publication",
                dry_run=True,
                resume=True,
                cached_bronze_enabled=False,
                health_server=False,
                health_port=8081,
            )

        out = capsys.readouterr().out
        assert "Dry-run mode: no data will be written" in out
        assert "Resume mode: continuing from last checkpoint" in out

    def test_cached_bronze_true_echoes_rebuild_resume_boundary_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Cached Bronze on composite run prints rebuild/resume boundary warning."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ):
            echo_composite_startup(
                composite="publication",
                dry_run=False,
                resume=False,
                cached_bronze_enabled=True,
                health_server=False,
                health_port=8081,
            )

        out = capsys.readouterr().out
        assert "outside the strict exact-replay boundary" in out
        assert "Cached Bronze is rebuild/resume evidence only" in out
        assert "strict exact replay remains source-run only" in out

    def test_cached_bronze_false_does_not_echo_boundary_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Boundary warning is omitted when cached Bronze is not enabled."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.composite.runtime.echo_health_server_info"
        ):
            echo_composite_startup(
                composite="publication",
                dry_run=False,
                resume=False,
                cached_bronze_enabled=False,
                health_server=False,
                health_port=8081,
            )

        out = capsys.readouterr().out
        assert "strict exact-replay boundary" not in out
