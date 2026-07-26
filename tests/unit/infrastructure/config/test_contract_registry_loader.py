"""Unit tests for the canonical contract-registry loader helpers."""

from __future__ import annotations

import ctypes
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import MagicMock, patch

import pytest
import yaml

from bioetl.infrastructure.config.contract_registry_loader import (
    DEFAULT_CONTRACT_REGISTRY_PATH,
    _is_likely_network_drive,
    _load_yaml_with_timeout,
    load_contract_registry_entries,
    load_contract_registry_entry,
    load_contract_registry_payload,
    resolve_contract_registry_path,
    try_load_contract_registry_entries,
    try_load_contract_registry_payload,
)

pytestmark = pytest.mark.unit


def _install_mock_kernel32(
    monkeypatch: pytest.MonkeyPatch, kernel32: MagicMock
) -> None:
    """Install a mock ``ctypes.windll.kernel32`` surface for Windows-drive probes."""
    windll = type("MockWindll", (), {"kernel32": kernel32})()
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)


def test_resolve_contract_registry_path_defaults_to_canonical_relative_path() -> None:
    assert resolve_contract_registry_path() == DEFAULT_CONTRACT_REGISTRY_PATH


def test_resolve_contract_registry_path_from_repo_root() -> None:
    repo_root = Path("/tmp/bioetl-repo")

    assert resolve_contract_registry_path(repo_root=repo_root) == (
        repo_root / DEFAULT_CONTRACT_REGISTRY_PATH
    )


def test_resolve_contract_registry_path_from_configs_root() -> None:
    configs_root = Path("/tmp/bioetl-repo/configs")

    assert resolve_contract_registry_path(configs_root=configs_root) == (
        configs_root / "base" / "contract_registry.yaml"
    )


def test_resolve_contract_registry_path_rejects_conflicting_roots() -> None:
    with pytest.raises(ValueError, match="either repo_root or configs_root"):
        resolve_contract_registry_path(
            repo_root=Path("/tmp/repo"),
            configs_root=Path("/tmp/repo/configs"),
        )


def test_resolve_contract_registry_path_uses_explicit_path() -> None:
    explicit_path = Path("/custom/path/registry.yaml")
    result = resolve_contract_registry_path(registry_path=explicit_path)
    assert result == explicit_path


class TestIsLikelyNetworkDrive:
    """Test network drive detection."""

    def test_returns_false_on_non_windows(self, monkeypatch):
        """Test that non-Windows systems return False."""
        monkeypatch.setattr("os.name", "posix")
        result = _is_likely_network_drive(Path("/some/path"))
        assert result is False

    def test_returns_true_for_unc_path(self, monkeypatch):
        """Test that UNC paths are detected as network paths."""
        monkeypatch.setattr("os.name", "nt")
        result = _is_likely_network_drive(Path("\\\\server\\share\\path"))
        assert result is True

    def test_returns_false_for_local_drive(self, monkeypatch):
        """Test that local drives return False."""
        monkeypatch.setattr("os.name", "nt")

        # Mock Windows API to return local drive type
        mock_kernel32 = MagicMock()
        mock_kernel32.GetDriveTypeW.return_value = 3  # DRIVE_FIXED

        _install_mock_kernel32(monkeypatch, mock_kernel32)

        result = _is_likely_network_drive(Path("C:\\local\\path"))
        assert result is False

    def test_returns_true_for_remote_drive(self, monkeypatch):
        """Test that remote drives return True."""
        monkeypatch.setattr("os.name", "nt")

        # Mock Windows API to return remote drive type
        mock_kernel32 = MagicMock()
        mock_kernel32.GetDriveTypeW.return_value = 4  # DRIVE_REMOTE

        _install_mock_kernel32(monkeypatch, mock_kernel32)

        result = _is_likely_network_drive(Path("Z:\\network\\path"))
        assert result is True

    def test_returns_false_on_detection_failure(self, monkeypatch):
        """Test that detection failures default to False."""
        monkeypatch.setattr("os.name", "nt")

        # Mock to raise exception
        mock_kernel32 = MagicMock()
        mock_kernel32.GetDriveTypeW.side_effect = OSError()

        _install_mock_kernel32(monkeypatch, mock_kernel32)

        result = _is_likely_network_drive(Path("C:\\path"))
        assert result is False

    def test_handles_missing_drive_attribute(self, monkeypatch):
        """Test handling of paths without drive attribute."""
        monkeypatch.setattr("os.name", "nt")

        # Mock path without drive
        mock_path = MagicMock()
        mock_path.drive = ""
        mock_path.__str__ = lambda: "/some/path"

        result = _is_likely_network_drive(mock_path)
        assert result is False

    def test_returns_false_when_windows_path_has_no_drive_prefix(self, monkeypatch):
        """Drive-less Windows paths should short-circuit before WinAPI probing."""
        monkeypatch.setattr("os.name", "nt")
        monkeypatch.setattr("os.path.splitdrive", lambda _value: ("", "relative/path"))

        assert _is_likely_network_drive(Path("relative/path")) is False


class TestLoadYamlWithTimeout:
    """Test timeout-protected YAML loading."""

    def test_loads_yaml_directly_for_local_drives(self, monkeypatch):
        """Test direct loading for local drives."""
        monkeypatch.setattr(
            "bioetl.infrastructure.config.contract_registry_loader._is_likely_network_drive",
            lambda x: False,
        )

        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.yaml"
            test_file.write_text("key: value", encoding="utf-8")

            result = _load_yaml_with_timeout(test_file)
            assert result == {"key": "value"}

    def test_loads_yaml_with_timeout_for_network_drives(self, monkeypatch):
        """Test timeout-protected loading for network drives."""
        monkeypatch.setattr(
            "bioetl.infrastructure.config.contract_registry_loader._is_likely_network_drive",
            lambda x: True,
        )

        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.yaml"
            test_file.write_text("key: value", encoding="utf-8")

            result = _load_yaml_with_timeout(test_file, timeout=5.0)
            assert result == {"key": "value"}

    def test_raises_timeout_on_slow_load(self, monkeypatch):
        """Test timeout exception for slow loading."""
        # Skip this test on Windows due to threading issues
        import sys

        if sys.platform == "win32":
            pytest.skip("Threading timeout test skipped on Windows")

        monkeypatch.setattr(
            "bioetl.infrastructure.config.contract_registry_loader._is_likely_network_drive",
            lambda x: True,
        )

        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.yaml"
            test_file.write_text("key: value", encoding="utf-8")

            original_read_text = Path.read_text

            def slow_read_text(self: Path, *args, **kwargs):
                if self == test_file:
                    sleep(0.1)  # Simulate slow network-drive read latency.
                return original_read_text(self, *args, **kwargs)

            monkeypatch.setattr(Path, "read_text", slow_read_text)

            with pytest.raises(TimeoutError, match="did not complete"):
                _load_yaml_with_timeout(test_file, timeout=0.01)

    def test_propagates_yaml_error(self, monkeypatch):
        """Test that YAML errors are propagated."""
        monkeypatch.setattr(
            "bioetl.infrastructure.config.contract_registry_loader._is_likely_network_drive",
            lambda x: False,
        )

        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "invalid.yaml"
            test_file.write_text("invalid: yaml: content:", encoding="utf-8")

            with pytest.raises(yaml.YAMLError):
                _load_yaml_with_timeout(test_file)

    def test_propagates_os_error(self, monkeypatch):
        """Test that OS errors are propagated."""
        monkeypatch.setattr(
            "bioetl.infrastructure.config.contract_registry_loader._is_likely_network_drive",
            lambda x: False,
        )

        with pytest.raises(OSError):
            _load_yaml_with_timeout(Path("/nonexistent/path.yaml"))

    def test_raises_value_error_when_yaml_root_is_not_a_mapping(self, monkeypatch):
        """Null/empty YAML roots are rejected as non-mapping payloads.

        ``yaml.safe_load("null")`` returns ``None``, which is not a mapping.
        The loader raises the mapping contract error on both local and
        network-drive paths (before the defensive ``result is None`` branch).
        """
        monkeypatch.setattr(
            "bioetl.infrastructure.config.contract_registry_loader._is_likely_network_drive",
            lambda x: True,
        )

        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "empty.yaml"
            _ = test_file.write_text("null", encoding="utf-8")

            with pytest.raises(ValueError, match="YAML root must be a mapping"):
                _ = _load_yaml_with_timeout(test_file)

    def test_raises_value_error_when_network_thread_leaves_empty_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Defensive branch: completed network thread with no payload and no error."""
        monkeypatch.setattr(
            "bioetl.infrastructure.config.contract_registry_loader._is_likely_network_drive",
            lambda _path: True,
        )

        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "empty.yaml"
            _ = test_file.write_text("key: value", encoding="utf-8")

            class ImmediateThread:
                """Stub Thread that finishes immediately without running target."""

                def __init__(
                    self,
                    target: object | None = None,
                    daemon: bool | None = None,
                ) -> None:
                    # Intentionally ignore target so result stays None.
                    del target, daemon

                def start(self) -> None:
                    return

                def join(self, timeout: float | None = None) -> None:
                    del timeout

                def is_alive(self) -> bool:
                    return False

            monkeypatch.setattr(
                "bioetl.infrastructure.config.contract_registry_loader.threading.Thread",
                ImmediateThread,
            )

            with pytest.raises(ValueError, match="YAML load returned None"):
                _ = _load_yaml_with_timeout(test_file)

    def test_reraises_thread_exception_for_network_drive_reads(self, monkeypatch):
        """Exceptions raised inside the timeout thread should be surfaced to callers."""
        monkeypatch.setattr(
            "bioetl.infrastructure.config.contract_registry_loader._is_likely_network_drive",
            lambda _path: True,
        )

        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.yaml"
            test_file.write_text("key: value", encoding="utf-8")

            def raising_read_text(self: Path, *args, **kwargs):
                del args, kwargs
                if self == test_file:
                    raise ValueError("boom")
                return Path.read_text(self, encoding="utf-8")

            monkeypatch.setattr(Path, "read_text", raising_read_text)

            with pytest.raises(ValueError, match="boom"):
                _load_yaml_with_timeout(test_file)


class TestLoadContractRegistryPayload:
    """Test contract registry payload loading."""

    def test_loads_valid_payload(self):
        """Test loading a valid payload."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "contract_registry.yaml"
            test_file.write_text("entries:\n  test:\n    value: 1", encoding="utf-8")

            result = load_contract_registry_payload(registry_path=test_file)
            assert result == {"entries": {"test": {"value": 1}}}

    def test_raises_file_not_found(self):
        """Test FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Contract registry not found"):
            load_contract_registry_payload(registry_path=Path("/nonexistent.yaml"))

    def test_wraps_timeout_error(self):
        """Test that timeout errors are wrapped with context."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.yaml"
            test_file.write_text("key: value", encoding="utf-8")

            with patch(
                "bioetl.infrastructure.config.contract_registry_loader._load_yaml_with_timeout",
                side_effect=TimeoutError("Timeout"),
            ):
                with pytest.raises(
                    TimeoutError, match="Contract registry load timeout"
                ):
                    load_contract_registry_payload(registry_path=test_file)

    def test_wraps_os_error(self):
        """Test that OS errors are wrapped with context."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.yaml"
            test_file.write_text("key: value", encoding="utf-8")

            with patch(
                "bioetl.infrastructure.config.contract_registry_loader._load_yaml_with_timeout",
                side_effect=OSError("Permission denied"),
            ):
                with pytest.raises(OSError, match="Failed to read contract registry"):
                    load_contract_registry_payload(registry_path=test_file)

    def test_wraps_yaml_error(self):
        """Test that YAML errors are wrapped with context."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.yaml"
            test_file.write_text("key: value", encoding="utf-8")

            with patch(
                "bioetl.infrastructure.config.contract_registry_loader._load_yaml_with_timeout",
                side_effect=yaml.YAMLError("Invalid YAML"),
            ):
                with pytest.raises(
                    ValueError, match="Malformed contract registry YAML"
                ):
                    load_contract_registry_payload(registry_path=test_file)

    def test_raises_value_error_for_non_dict_root(self):
        """Non-mapping YAML roots fail during timed YAML load (mapping contract)."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "invalid.yaml"
            test_file.write_text("- item1\n- item2", encoding="utf-8")

            with pytest.raises(ValueError, match="YAML root must be a mapping"):
                load_contract_registry_payload(registry_path=test_file)


class TestTryLoadContractRegistryPayload:
    """Test best-effort payload loading."""

    def test_returns_payload_on_success(self):
        """Test returning payload when load succeeds."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "contract_registry.yaml"
            test_file.write_text("entries: {}", encoding="utf-8")

            result = try_load_contract_registry_payload(registry_path=test_file)
            assert result == {"entries": {}}

    def test_returns_none_on_file_not_found(self):
        """Test returning None for missing file."""
        result = try_load_contract_registry_payload(
            registry_path=Path("/nonexistent.yaml")
        )
        assert result is None

    def test_returns_none_on_os_error(self):
        """Test returning None on OS errors."""
        with patch(
            "bioetl.infrastructure.config.contract_registry_loader.load_contract_registry_payload",
            side_effect=OSError("Permission denied"),
        ):
            result = try_load_contract_registry_payload(
                registry_path=Path("/test.yaml")
            )
            assert result is None

    def test_returns_none_on_value_error_for_invalid_payload(self):
        """Test returning None on validation errors."""
        with patch(
            "bioetl.infrastructure.config.contract_registry_loader.load_contract_registry_payload",
            side_effect=ValueError("Invalid format"),
        ):
            result = try_load_contract_registry_payload(
                registry_path=Path("/test.yaml")
            )
            assert result is None


class TestLoadContractRegistryEntries:
    """Test contract registry entries loading."""

    def test_loads_valid_entries(self):
        """Test loading valid entries mapping."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "contract_registry.yaml"
            test_file.write_text(
                "entries:\n  contract1:\n    version: 1.0\n  contract2:\n    version: 2.0",
                encoding="utf-8",
            )

            result = load_contract_registry_entries(registry_path=test_file)
            assert result == {
                "contract1": {"version": 1.0},
                "contract2": {"version": 2.0},
            }

    def test_normalizes_contract_ref_to_string(self):
        """Test that contract refs are normalized to strings."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "contract_registry.yaml"
            test_file.write_text(
                "entries:\n  123:\n    version: 1.0\n  456:\n    version: 2.0",
                encoding="utf-8",
            )

            result = load_contract_registry_entries(registry_path=test_file)
            assert "123" in result
            assert "456" in result
            assert isinstance(list(result.keys())[0], str)

    def test_raises_value_error_for_missing_entries(self):
        """Test ValueError when entries key is missing."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "invalid.yaml"
            test_file.write_text("other_key: value", encoding="utf-8")

            with pytest.raises(ValueError, match="entries must be a mapping"):
                load_contract_registry_entries(registry_path=test_file)

    def test_raises_value_error_for_non_dict_entries(self):
        """Test ValueError when entries is not a mapping."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "invalid.yaml"
            test_file.write_text("entries:\n  - item1\n  - item2", encoding="utf-8")

            with pytest.raises(ValueError, match="entries must be a mapping"):
                load_contract_registry_entries(registry_path=test_file)

    def test_raises_value_error_for_non_dict_entry(self):
        """Test ValueError when individual entry is not a mapping."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "invalid.yaml"
            test_file.write_text("entries:\n  contract1: not_a_dict", encoding="utf-8")

            with pytest.raises(ValueError, match="entry must be a mapping"):
                load_contract_registry_entries(registry_path=test_file)


class TestTryLoadContractRegistryEntries:
    """Test best-effort entries loading."""

    def test_returns_entries_on_success(self):
        """Test returning entries when load succeeds."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "contract_registry.yaml"
            test_file.write_text("entries:\n  test:\n    value: 1", encoding="utf-8")

            result = try_load_contract_registry_entries(registry_path=test_file)
            assert result == {"test": {"value": 1}}

    def test_returns_empty_dict_on_file_not_found(self):
        """Test returning empty dict for missing file."""
        result = try_load_contract_registry_entries(
            registry_path=Path("/nonexistent.yaml")
        )
        assert result == {}

    def test_returns_empty_dict_on_os_error(self):
        """Test returning empty dict on OS errors."""
        with patch(
            "bioetl.infrastructure.config.contract_registry_loader.load_contract_registry_entries",
            side_effect=OSError("Permission denied"),
        ):
            result = try_load_contract_registry_entries(
                registry_path=Path("/test.yaml")
            )
            assert result == {}

    def test_returns_empty_dict_on_value_error(self):
        """Test returning empty dict on validation errors."""
        with patch(
            "bioetl.infrastructure.config.contract_registry_loader.load_contract_registry_entries",
            side_effect=ValueError("Invalid format"),
        ):
            result = try_load_contract_registry_entries(
                registry_path=Path("/test.yaml")
            )
            assert result == {}


class TestLoadContractRegistryEntry:
    """Test single contract registry entry loading."""

    def test_loads_specific_entry(self):
        """Test loading a specific entry by contract_ref."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "contract_registry.yaml"
            test_file.write_text(
                "entries:\n  contract1:\n    version: 1.0\n  contract2:\n    version: 2.0",
                encoding="utf-8",
            )

            result = load_contract_registry_entry("contract1", registry_path=test_file)
            assert result == {"version": 1.0}

    def test_raises_key_error_for_missing_entry(self):
        """Test KeyError when contract_ref is not found."""
        with TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "contract_registry.yaml"
            test_file.write_text(
                "entries:\n  contract1:\n    version: 1.0", encoding="utf-8"
            )

            with pytest.raises(KeyError, match="Contract registry entry not found"):
                load_contract_registry_entry("nonexistent", registry_path=test_file)
