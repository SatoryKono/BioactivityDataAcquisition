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
"""Tests for shared publication ISSN field assembly."""

from __future__ import annotations

import pytest

from collections.abc import Iterable

from bioetl.application.pipelines.common.publication_issn import build_issn_fields


pytestmark = pytest.mark.unit


def _serialize(values: Iterable[str] | None) -> str | None:
    if values is None:
        return None
    return "[" + ",".join(f'"{value}"' for value in values) + "]"


def test_build_issn_fields_from_scalar() -> None:
    fields = build_issn_fields(
        "0028-0836",
        serialize_json_list=_serialize,
    )

    assert fields == {"issn": "0028-0836", "issn_list": '["0028-0836"]'}


def test_build_issn_fields_from_comma_delimited_string() -> None:
    fields = build_issn_fields(
        "0028-0836, 1476-4687",
        serialize_json_list=_serialize,
    )

    assert fields == {
        "issn": "0028-0836",
        "issn_list": '["0028-0836","1476-4687"]',
    }


def test_build_issn_fields_from_missing_value() -> None:
    fields = build_issn_fields(None, serialize_json_list=_serialize)

    assert fields == {"issn": None, "issn_list": None}


def test_build_issn_fields_from_sequence_omits_none_values() -> None:
    fields = build_issn_fields(
        ["0028-0836", None, "1476-4687"],
        serialize_json_list=_serialize,
    )

    assert fields == {
        "issn": "0028-0836",
        "issn_list": '["0028-0836","1476-4687"]',
    }


def test_build_issn_fields_from_non_sequence_scalar() -> None:
    fields = build_issn_fields(12345678, serialize_json_list=_serialize)

    assert fields == {"issn": "12345678", "issn_list": '["12345678"]'}
