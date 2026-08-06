# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for adapter-side DOI transport prefix stripping."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.common.doi_helpers import strip_doi_transport_prefix

pytestmark = pytest.mark.unit

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1234/test"


class TestStripDoiTransportPrefix:
    """Tests for strip_doi_transport_prefix."""

    def test_strips_https_and_http_doi_org_prefixes(self) -> None:
        """URL prefixes https://doi.org/ and http://doi.org/ are removed."""
        assert (
            strip_doi_transport_prefix("https://doi.org/10.1234/test") == "10.1234/test"
        )
        assert strip_doi_transport_prefix(LEGACY_HTTP_DOI) == "10.1234/test"

    def test_strips_dx_doi_org_prefixes(self) -> None:
        """Legacy dx.doi.org URL prefixes are removed."""
        assert (
            strip_doi_transport_prefix("https://dx.doi.org/10.1234/test")
            == "10.1234/test"
        )
        assert (
            strip_doi_transport_prefix("HTTP://DX.DOI.ORG/10.1234/test")
            == "10.1234/test"
        )

    def test_strips_doi_scheme_prefixes(self) -> None:
        """doi: and DOI: scheme prefixes are removed (case-insensitive)."""
        assert strip_doi_transport_prefix("doi:10.1234/test") == "10.1234/test"
        assert strip_doi_transport_prefix("DOI:10.1234/test") == "10.1234/test"
        assert strip_doi_transport_prefix("DoI:10.1234/test") == "10.1234/test"

    def test_unprefixed_doi_passthrough(self) -> None:
        """Bare DOI strings are returned unchanged."""
        assert strip_doi_transport_prefix("10.1234/test") == "10.1234/test"
        assert strip_doi_transport_prefix("10.1038/NATURE") == "10.1038/NATURE"

    def test_strips_surrounding_whitespace(self) -> None:
        """Leading/trailing whitespace is stripped before prefix matching."""
        assert (
            strip_doi_transport_prefix("  https://doi.org/10.1234/test  ")
            == "10.1234/test"
        )
        assert strip_doi_transport_prefix(f"\t{LEGACY_HTTP_DOI}\t") == "10.1234/test"

    def test_allow_uppercase_prefix_flag_is_ignored_but_accepted(self) -> None:
        """Deprecated allow_uppercase_prefix remains accepted for API compat."""
        assert (
            strip_doi_transport_prefix(
                "DOI:10.1234/test",
                allow_uppercase_prefix=False,
            )
            == "10.1234/test"
        )
        assert (
            strip_doi_transport_prefix(
                "DOI:10.1234/test",
                allow_uppercase_prefix=True,
            )
            == "10.1234/test"
        )
