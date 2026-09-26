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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for package version metadata."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError

import pytest

import bioetl as version_module
from bioetl import get_version


@pytest.mark.unit
class TestGetVersion:
    """Tests for get_version function."""

    def test_returns_string(self) -> None:
        """Test that get_version always returns a string."""
        result = get_version()
        assert isinstance(result, str)

    def test_returns_version_or_unknown(self) -> None:
        """Test that get_version returns a version string or 'unknown'."""
        result = get_version()
        # Either a valid semver-like string or 'unknown'
        assert result == "unknown" or len(result) > 0

    def test_no_exception_raised(self) -> None:
        """Test that get_version does not raise any exception."""
        # Should not raise even if package is not installed
        result = get_version()
        assert result is not None

    def test_returns_unknown_when_declared_and_installed_versions_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Version lookup should fail closed when neither source is present."""
        import bioetl

        def missing_package_version(_: str) -> str:
            raise PackageNotFoundError("bioetl")

        monkeypatch.delattr(bioetl, "__version__", raising=True)
        monkeypatch.setattr(version_module, "_pkg_version", missing_package_version)

        assert version_module.get_version() == "unknown"

    def test_uses_installed_version_when_declared_version_is_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Installed metadata remains the fallback for an empty declaration."""
        monkeypatch.setattr(version_module, "__version__", "")
        monkeypatch.setattr(version_module, "_pkg_version", lambda _: "6.2.0")

        assert version_module.get_version() == "6.2.0"
