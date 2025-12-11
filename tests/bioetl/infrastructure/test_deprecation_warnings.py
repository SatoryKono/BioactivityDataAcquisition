"""Tests for deprecation warnings in infrastructure shim modules.

These tests verify that importing from deprecated module paths
emits the expected DeprecationWarning messages.
"""

import importlib
import sys
import warnings

import pytest


class TestConfigModelsDeprecation:
    """Tests for bioetl.infrastructure.config.models deprecation."""

    def test_config_models_deprecation_warning(self) -> None:
        """Importing from infrastructure.config.models emits DeprecationWarning."""
        # Remove from cache if already imported
        module_name = "bioetl.infrastructure.config.models"
        if module_name in sys.modules:
            del sys.modules[module_name]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            importlib.import_module(module_name)

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        # Check for the actual deprecation message from infrastructure.config.models
        # Iterate over all warnings as other warnings might be emitted first
        found = False
        for warning in deprecation_warnings:
            message_str = str(warning.message)
            if (
                "infrastructure.config.models" in message_str
                or "domain.configs" in message_str
            ):
                found = True
                break

        assert (
            found
        ), f"Expected warning not found in: {[str(w.message) for w in deprecation_warnings]}"

    def test_config_models_exports_available(self) -> None:
        """Deprecated module still exports all expected symbols."""
        # Suppress warning for this test
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.infrastructure.config import models

        # Verify key exports are available
        assert hasattr(models, "PipelineConfig")
        assert hasattr(models, "RuntimeConfig")
        assert hasattr(models, "HttpClientConfig")


class TestCsvRecordSourceDeprecation:
    """Tests for bioetl.infrastructure.files.csv_record_source deprecation."""

    def test_csv_record_source_deprecation_warning(self) -> None:
        """Importing from infrastructure.files.csv_record_source raises ImportError."""
        module_name = "bioetl.infrastructure.files.csv_record_source"
        if module_name in sys.modules:
            del sys.modules[module_name]

        with pytest.raises(ImportError, match="has been removed"):
            importlib.import_module(module_name)

    # test_csv_record_source_exports_available removed as module is removed


class TestConstantsDeprecation:
    """Tests for bioetl.infrastructure.constants deprecation."""

    def test_constants_deprecation_warning(self) -> None:
        """Importing from infrastructure.constants emits DeprecationWarning."""
        module_name = "bioetl.infrastructure.constants"
        if module_name in sys.modules:
            del sys.modules[module_name]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            importlib.import_module(module_name)

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        assert "infrastructure.constants" in str(deprecation_warnings[0].message)
        assert "infrastructure.settings.files" in str(deprecation_warnings[0].message)
        assert "v2.0" in str(deprecation_warnings[0].message)

    def test_constants_exports_available(self) -> None:
        """Deprecated module still exports all expected constants."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.infrastructure import constants

        assert hasattr(constants, "MAX_FILE_RETRIES")
        assert hasattr(constants, "RETRY_DELAY_SEC")
        assert hasattr(constants, "CHECKSUM_CHUNK_SIZE")

    def test_constants_values_match_new_location(self) -> None:
        """Constants values match between old and new locations."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.infrastructure import constants

        from bioetl.infrastructure.settings.files import (
            CHECKSUM_CHUNK_SIZE,
            MAX_FILE_RETRIES,
            RETRY_DELAY_SEC,
        )

        assert constants.MAX_FILE_RETRIES == MAX_FILE_RETRIES
        assert constants.RETRY_DELAY_SEC == RETRY_DELAY_SEC
        assert constants.CHECKSUM_CHUNK_SIZE == CHECKSUM_CHUNK_SIZE


class TestNewImportsNoWarnings:
    """Verify new import paths do not emit deprecation warnings."""

    def test_domain_configs_no_warning(self) -> None:
        """Importing from domain.configs does not emit DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from bioetl.domain.configs import PipelineConfig  # noqa: F401

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        # Filter out unrelated deprecation warnings
        relevant_warnings = [
            x
            for x in deprecation_warnings
            if "infrastructure.config.models" in str(x.message)
        ]
        assert len(relevant_warnings) == 0

    def test_settings_files_no_warning(self) -> None:
        """Importing from settings.files does not emit DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from bioetl.infrastructure.settings.files import (  # noqa: F401
                MAX_FILE_RETRIES,
            )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        relevant_warnings = [
            x
            for x in deprecation_warnings
            if "infrastructure.constants" in str(x.message)
        ]
        assert len(relevant_warnings) == 0

    def test_application_csv_record_source_no_warning(self) -> None:
        """Importing from application layer does not emit DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from bioetl.application.files.csv_record_source import (  # noqa: F401
                CsvRecordSourceImpl,
            )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        relevant_warnings = [
            x
            for x in deprecation_warnings
            if "infrastructure.files.csv_record_source" in str(x.message)
        ]
        assert len(relevant_warnings) == 0
