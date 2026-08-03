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
"""Tests for UniProt response parser helpers."""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock

from bioetl.infrastructure.adapters.uniprot.response_parser import (
    parse_uniprot_protein_response,
)


pytestmark = pytest.mark.unit


def test_parse_uniprot_protein_response_returns_records_and_cursor() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "results": [{"primaryAccession": "P12345"}],
        "nextCursor": "cursor-1",
    }

    assert parse_uniprot_protein_response(response) == (
        [{"primaryAccession": "P12345"}],
        "cursor-1",
    )


def test_parse_uniprot_protein_response_handles_malformed_payload() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = "bad-payload"

    assert parse_uniprot_protein_response(response) == ([], None)


def test_parse_uniprot_protein_response_filters_malformed_results_and_cursor() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "results": [{"primaryAccession": "P12345"}, "bad-record", None],
        "nextCursor": 123,
    }

    assert parse_uniprot_protein_response(response) == (
        [{"primaryAccession": "P12345"}],
        None,
    )


def test_parse_uniprot_protein_response_returns_empty_for_non_200_status() -> None:
    response = MagicMock()
    response.status_code = 503

    assert parse_uniprot_protein_response(response) == ([], None)
    response.json.assert_not_called()
