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
"""Focused tests for UniProt ID-mapping URL trust policy."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.uniprot._idmapping_url_policy import (
    trusted_idmapping_url,
)


pytestmark = pytest.mark.unit

_BASE = "https://rest.uniprot.org"


def test_trusted_idmapping_url_accepts_same_origin_status_path() -> None:
    resolved = trusted_idmapping_url(_BASE, "idmapping/status/job-1")

    assert resolved == "https://rest.uniprot.org/idmapping/status/job-1"


def test_trusted_idmapping_url_accepts_http_default_port() -> None:
    resolved = trusted_idmapping_url(
        "http://rest.uniprot.org",
        "idmapping/status/job-1",
    )

    assert resolved == "http://rest.uniprot.org/idmapping/status/job-1"


def test_trusted_idmapping_url_rejects_query_in_base() -> None:
    with pytest.raises(ValueError, match="query and fragment"):
        trusted_idmapping_url(f"{_BASE}?q=1", "idmapping/status/job-1")


def test_trusted_idmapping_url_rejects_fragment_in_base() -> None:
    with pytest.raises(ValueError, match="query and fragment"):
        trusted_idmapping_url(f"{_BASE}#frag", "idmapping/status/job-1")


def test_trusted_idmapping_url_rejects_fragment_in_candidate() -> None:
    with pytest.raises(ValueError, match="untrusted UniProt ID mapping URL"):
        trusted_idmapping_url(_BASE, "idmapping/status/job-1#frag")


def test_trusted_idmapping_url_rejects_cross_origin_candidate() -> None:
    with pytest.raises(ValueError, match="untrusted UniProt ID mapping URL"):
        trusted_idmapping_url(_BASE, "https://evil.example/idmapping/status/job-1")


def test_trusted_idmapping_url_rejects_userinfo() -> None:
    with pytest.raises(ValueError, match="userinfo is forbidden"):
        trusted_idmapping_url(
            "https://user:pass@rest.uniprot.org",
            "idmapping/status/job-1",
        )


def test_trusted_idmapping_url_rejects_invalid_scheme() -> None:
    with pytest.raises(ValueError, match="invalid UniProt ID mapping base URL"):
        trusted_idmapping_url("ftp://rest.uniprot.org", "idmapping/status/job-1")


def test_trusted_idmapping_url_rejects_invalid_port() -> None:
    with pytest.raises(ValueError, match="invalid port"):
        trusted_idmapping_url(
            "https://rest.uniprot.org:notaport",
            "idmapping/status/job-1",
        )


def test_trusted_idmapping_url_rejects_missing_hostname() -> None:
    with pytest.raises(ValueError, match="invalid UniProt ID mapping base URL"):
        trusted_idmapping_url("https:///idmapping", "status/job-1")


def test_trusted_idmapping_url_rejects_backslash_in_path() -> None:
    with pytest.raises(ValueError, match="untrusted UniProt ID mapping path"):
        trusted_idmapping_url(_BASE, "status/%5Cjob")


def test_trusted_idmapping_url_rejects_parent_directory_segment() -> None:
    with pytest.raises(ValueError, match="untrusted UniProt ID mapping path"):
        trusted_idmapping_url(_BASE, "idmapping/status/%2e%2e/job-1")


def test_trusted_idmapping_url_rejects_path_outside_idmapping_api() -> None:
    with pytest.raises(ValueError, match="outside the UniProt ID mapping API"):
        trusted_idmapping_url("https://rest.uniprot.org/uniprotkb", "P05067")
