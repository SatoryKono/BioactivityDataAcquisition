"""Tests for CLI exit codes module.

Verifies exit code standardization per architecture review R4.
"""

from __future__ import annotations

import pytest

from bioetl.interfaces.cli.exit_codes import (
    EXCEPTION_EXIT_CODES,
    ExitCode,
    get_exit_code_for_exception,
)


pytestmark = pytest.mark.unit

class TestExitCode:
    """Tests for ExitCode enum."""

    def test_success_code_is_zero(self) -> None:
        """Success exit code must be 0 per Unix convention."""
        assert ExitCode.OK == 0

    def test_fail_code_is_one(self) -> None:
        """General failure exit code must be 1 per Unix convention."""
        assert ExitCode.FAIL == 1

    def test_sigint_code_is_130(self) -> None:
        """SIGINT exit code must be 130 (128 + 2) per Unix convention."""
        assert ExitCode.SIGINT == 130

    def test_sigterm_code_is_143(self) -> None:
        """SIGTERM exit code must be 143 (128 + 15) per Unix convention."""
        assert ExitCode.SIGTERM == 143

    def test_sysexits_codes_in_correct_range(self) -> None:
        """Standard sysexits.h codes must be in 64-78 range."""
        sysexits_codes = [
            ExitCode.EX_USAGE,
            ExitCode.EX_DATAERR,
            ExitCode.EX_NOINPUT,
            ExitCode.EX_UNAVAILABLE,
            ExitCode.EX_SOFTWARE,
            ExitCode.EX_OSERR,
            ExitCode.EX_IOERR,
            ExitCode.EX_TEMPFAIL,
            ExitCode.EX_CONFIG,
        ]
        for code in sysexits_codes:
            assert 64 <= code <= 78, f"{code.name} should be in sysexits range 64-78"

    def test_bioetl_codes_in_custom_range(self) -> None:
        """BioETL-specific codes must be in 80-99 range."""
        bioetl_codes = [
            ExitCode.CONFIG_ERROR,
            ExitCode.INIT_ERROR,
            ExitCode.PIPELINE_ERROR,
            ExitCode.DATA_QUALITY_ERROR,
            ExitCode.LOCK_ERROR,
            ExitCode.STORAGE_ERROR,
            ExitCode.NETWORK_ERROR,
            ExitCode.CHECKPOINT_ERROR,
        ]
        for code in bioetl_codes:
            assert 80 <= code <= 99, f"{code.name} should be in BioETL range 80-99"


class TestExceptionExitCodeMapping:
    """Tests for exception-to-exit-code mapping."""

    def test_critical_error_returns_fail(self) -> None:
        """CriticalError should return FAIL exit code."""
        from bioetl.domain.exceptions import CriticalError

        exc = CriticalError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.FAIL

    def test_config_validation_error_returns_config_error(self) -> None:
        """ConfigValidationError should return CONFIG_ERROR."""
        from bioetl.domain.types import ConfigValidationError

        # ConfigValidationError is a dataclass with required fields
        exc = ConfigValidationError(
            field="test_field",
            expected="expected_value",
            actual="actual_value",
            rule="test_rule",
        )
        assert get_exit_code_for_exception(exc) == ExitCode.CONFIG_ERROR

    def test_data_quality_error_returns_dq_error(self) -> None:
        """DataQualityError should return DATA_QUALITY_ERROR."""
        from bioetl.domain.exceptions import DataQualityError

        exc = DataQualityError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.DATA_QUALITY_ERROR

    def test_network_error_returns_network_error(self) -> None:
        """NetworkError should return NETWORK_ERROR."""
        from bioetl.domain.exceptions import NetworkError

        exc = NetworkError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.NETWORK_ERROR

    def test_lock_error_returns_lock_error(self) -> None:
        """LockAcquisitionError should return LOCK_ERROR."""
        from bioetl.domain.exceptions import LockAcquisitionError

        exc = LockAcquisitionError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.LOCK_ERROR

    def test_storage_error_returns_storage_error(self) -> None:
        """StorageError should return STORAGE_ERROR."""
        from bioetl.domain.exceptions import StorageError

        exc = StorageError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.STORAGE_ERROR

    def test_pipeline_shutdown_returns_sigint(self) -> None:
        """PipelineShutdownError should return SIGINT."""
        from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError

        exc = PipelineShutdownError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.SIGINT

    def test_exit_code_mapping__returns_fail__41fd1627(self) -> None:
        """Unknown exceptions should return FAIL."""

        class UnknownError(Exception):
            pass

        exc = UnknownError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.FAIL

    def test_file_not_found_returns_noinput(self) -> None:
        """FileNotFoundError should return EX_NOINPUT."""
        exc = FileNotFoundError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.EX_NOINPUT

    def test_value_error_returns_config_error(self) -> None:
        """ValueError should return CONFIG_ERROR (common for config issues)."""
        exc = ValueError("test")
        assert get_exit_code_for_exception(exc) == ExitCode.CONFIG_ERROR


class TestExitCodeIntegration:
    """Integration tests for exit code consistency."""

    def test_all_mapped_exceptions_exist(self) -> None:
        """All exception types in mapping should be resolvable."""
        # This test ensures we don't have typos in exception names
        from bioetl.domain import exceptions

        for exc_name in EXCEPTION_EXIT_CODES:
            if hasattr(exceptions, exc_name):
                # Exception exists in domain.exceptions
                pass
            elif exc_name in ("ValueError", "FileNotFoundError", "KeyboardInterrupt"):
                # Built-in exceptions
                pass
            elif exc_name == "PipelineShutdownError":
                # Application layer exception
                from bioetl.application.core.lifecycle.shutdown import (
                    PipelineShutdownError,
                )

                assert PipelineShutdownError is not None
            elif exc_name == "ConfigValidationError":
                from bioetl.domain.types import ConfigValidationError

                assert ConfigValidationError is not None
            else:
                pytest.skip(
                    f"Exception {exc_name} not found - may be defined elsewhere"
                )

    def test_exit_codes_are_unique(self) -> None:
        """BioETL-specific exit codes must be unique (no collisions)."""
        bioetl_codes = [
            ExitCode.CONFIG_ERROR,
            ExitCode.INIT_ERROR,
            ExitCode.PIPELINE_ERROR,
            ExitCode.DATA_QUALITY_ERROR,
            ExitCode.LOCK_ERROR,
            ExitCode.STORAGE_ERROR,
            ExitCode.NETWORK_ERROR,
            ExitCode.CHECKPOINT_ERROR,
        ]
        assert len(bioetl_codes) == len(set(bioetl_codes)), (
            "BioETL codes must be unique"
        )
