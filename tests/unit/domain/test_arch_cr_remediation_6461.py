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
"""Regression coverage for CodeRabbit architecture remediation (#6461 family)."""

from __future__ import annotations

import pytest

from bioetl.domain.exceptions._redaction import _redact, _redact_string
from bioetl.domain.filtering._filter_primitives import check_exclude_if_present
from bioetl.domain.immutability import (
    FrozenDict,
    FrozenList,
    deep_freeze_json,
    deep_thaw_json,
)
from bioetl.domain.normalization.profiles._normalization_helpers import (
    _normalizer_accepts_record_context,
    _normalizer_ref,
)
from bioetl.domain.ports import (
    ExportJobStatus,
    ForeignKeyReconciliationLayer,
    ForeignKeyReconciliationRequest,
)
from bioetl.domain.ports.workflow_row_reconciliation import (
    RowReconciliationLayer,
    RowReconciliationResult,
    RowReconciliationTypePolicy,
)

pytestmark = pytest.mark.unit


def test_redaction_covers_basic_auth_and_cookie() -> None:
    text = "Authorization: Basic dXNlcjpwYXNz Cookie: session=abc password=xyz"
    redacted = _redact_string(text)
    assert "dXNlcjpwYXNz" not in redacted
    assert "session=abc" not in redacted
    assert "xyz" not in redacted
    assert "[REDACTED]" in redacted


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('token="escaped\\"quote"', "token=[REDACTED]"),
        ("password='escaped\\'quote'", "password=[REDACTED]"),
    ],
)
def test_redaction_handles_escaped_quotes(text: str, expected: str) -> None:
    assert _redact_string(text) == expected


def test_redaction_preserves_escaped_quotes_without_exposing_secret() -> None:
    secret = r"alpha\" beta"

    redacted = _redact_string(f'password="{secret}" safe-tail')

    assert secret not in redacted
    assert redacted == "password=[REDACTED] safe-tail"


def test_redaction_handles_long_unterminated_escaped_secret() -> None:
    text = 'token="' + ("\\" * 30_000) + "&"

    # Linear scan consumes an unterminated quoted value through end-of-string.
    assert _redact_string(text) == "token=[REDACTED]"


def test_redaction_handles_cyclic_context() -> None:
    payload: dict[str, object] = {"token": "secret-value"}
    payload["self"] = payload
    redacted = _redact(payload)
    assert isinstance(redacted, dict)
    assert redacted["token"] == "[REDACTED]"
    assert redacted["self"] == "[REDACTED CYCLE]"


def test_frozen_containers_block_base_class_mutation() -> None:
    frozen_list = deep_freeze_json([1, {"a": 2}])
    frozen_dict = deep_freeze_json({"k": [3]})
    assert isinstance(frozen_list, FrozenList)
    assert isinstance(frozen_dict, FrozenDict)
    with pytest.raises(TypeError):
        list.append(frozen_list, 9)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        dict.__setitem__(frozen_dict, "x", 1)  # type: ignore[arg-type]
    thawed = deep_thaw_json(frozen_dict)
    assert thawed == {"k": [3]}
    assert isinstance(thawed, dict)


def test_deep_freeze_json_rejects_non_string_keys() -> None:
    with pytest.raises(TypeError, match="JSON object keys must be strings"):
        deep_freeze_json({1: "a"})


def test_row_reconciliation_result_deep_freezes_rows() -> None:
    nested: dict[str, object] = {"child": {"x": 1}}
    result = RowReconciliationResult(
        layer=RowReconciliationLayer.SILVER,
        left_table="left",
        right_table="right",
        left_columns=("id",),
        right_columns=("id",),
        left_primary_keys=("id",),
        input_left_rows=1,
        input_right_rows=1,
        kept_rows=1,
        excluded_rows=0,
        null_key_rows_left=0,
        null_key_rows_right=0,
        distinct_right_keys=1,
        rows=(nested,),
        implementation="test",
        type_policy=RowReconciliationTypePolicy.STRICT,
    )
    row = result.rows[0]
    assert isinstance(row, FrozenDict)
    with pytest.raises(TypeError):
        dict.__setitem__(row, "new", 2)  # type: ignore[arg-type]


def test_fk_request_layers_are_keyword_only() -> None:
    request = ForeignKeyReconciliationRequest(
        "src",
        "ref",
        "sk",
        "rk",
        ("pk",),
        source_layer="gold",
        reference_layer="silver",
    )
    assert request.source_layer == "gold"
    assert request.effective_mutation_layer == "gold"
    assert request.source_keys is None


def test_ports_facade_exports_new_symbols() -> None:
    assert ExportJobStatus.REQUESTED.value == "requested"
    layer: ForeignKeyReconciliationLayer = "silver"
    assert layer == "silver"


def test_normalizer_ref_rejects_lambda_and_unhashable_accepts_context() -> None:
    def named(value: object, *, record: object | None = None) -> object:
        del record
        return value

    assert "named" in _normalizer_ref(named)
    assert _normalizer_accepts_record_context(named) is True

    class UnhashableNormalizer:
        __hash__ = None  # type: ignore[assignment]

        def __call__(self, value: object, *, record: object | None = None) -> object:
            del record
            return value

    unhashable = UnhashableNormalizer()
    # Must not raise TypeError from hashing the callable.
    assert _normalizer_accepts_record_context(unhashable) is True

    with pytest.raises(TypeError, match="lambda"):
        _normalizer_ref(lambda value: value)


def test_exclude_if_present_treats_empty_containers_as_absent() -> None:
    record = {"a": [], "b": {}, "c": set(), "d": "keep"}
    assert check_exclude_if_present(("a", "b", "c"), record) is True
    assert check_exclude_if_present(("d",), record) is False
