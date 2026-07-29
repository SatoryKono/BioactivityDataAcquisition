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
"""Focused tests for CrossRef publication field extractors."""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.crossref._publication_field_extractors import (
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
)


pytestmark = pytest.mark.unit


def test_extract_journal_and_pagination_fields() -> None:
    publication = {
        "container-title": ["Nature", "Nature Publishing Group"],
        "ISSN": ["0028-0836", "1476-4687"],
        "publisher": "Springer Nature",
        "volume": "42",
        "issue": "3",
        "page": "123-145",
    }

    assert extract_journal_info(publication) == {
        "journal": "Nature",
        "issn": "0028-0836",
        "issn_list": ["0028-0836", "1476-4687"],
        "publisher": "Springer Nature",
    }
    assert extract_page_info(publication) == {
        "volume": "42",
        "issue": "3",
        "page_first": "123",
        "page_last": "145",
    }


def test_extract_dates_and_published_date_handle_partial_date_parts() -> None:
    publication = {
        "published-print": {"date-parts": [[2023, 6, 15]]},
        "published-online": {"date-parts": [[2023, 5]]},
        "published": {"date-parts": [[2023]]},
    }

    assert extract_dates(publication) == {
        "published_print": "2023-06-15",
        "published_online": "2023-05-31",
    }
    assert extract_published_date(publication) == "2023-12-31"


def test_extract_license_content_domain_and_issn_type_are_defensive() -> None:
    publication = {
        "license": [
            {"URL": "https://license1.example"},
            {"URL": "https://license2.example"},
        ],
        "content-domain": {"domain": ["nature.com"], "crossmark-restriction": True},
        "issn-type": [
            {"value": "0006-291X", "type": "print"},
            {"value": "1090-2104", "type": "electronic"},
            "bad",
        ],
    }

    assert extract_license_url(publication) == "https://license1.example"
    assert extract_content_domain(publication) == {
        "content_domain_domains": ["nature.com"],
        "content_domain_crossmark_restriction": True,
    }
    assert extract_issn_by_type(publication) == {
        "issn_print": "0006-291X",
        "issn_electronic": "1090-2104",
    }
