# pyright: reportArgumentType=false
"""Residual closeout coverage for domain/exceptions CR-FULL #8155-#8165."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from bioetl.domain.exceptions import (
    ApiError,
    BioETLError,
    BucketNotFoundError,
    DataValidationError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
    get_domain_exception_context,
)
from bioetl.domain.exceptions._redaction import _redact_sequence
from bioetl.domain.exceptions.base_exceptions import BioETLDomainError
from bioetl.domain.exceptions.network_rate_limit_helpers import resolve_rate_limit_params
from bioetl.domain.exceptions.pipeline_shutdown import (
    PipelineShutdownError,
    ShutdownReason,
)
from bioetl.domain.exceptions.storage._delta import (
    DeltaSchemaValidationError,
    _build_schema_validation_message,
)
from bioetl.domain.exceptions.storage._storage import (
    BronzeValidationError,
    CachedBronzeEmptyError,
    UploadError,
)
from bioetl.domain.exceptions.validation import SchemaViolationError
from bioetl.domain.types import ErrorType


def test_redact_sequence_uses_plain_list_and_tuple() -> None:
    class CustomList(list):
        pass

    class CustomTuple(tuple):
        pass

    redacted_list = _redact_sequence(CustomList(["secret-token-value"]), "token", seen=set())
    redacted_tuple = _redact_sequence(CustomTuple(("secret-token-value",)), "token", seen=set())
    assert type(redacted_list) is list
    assert type(redacted_tuple) is tuple


def test_bioetl_error_structured_context_redacts_secrets() -> None:
    err = BioETLError("boom", reason_code="R1", api_key="super-secret-key")
    payload = err.to_structured_context(extra_token="also-secret")
    assert payload["error_type"] == "BioETLError"
    assert payload["reason_code"] == "R1"
    assert "super-secret" not in str(payload.values())
    assert "also-secret" not in str(payload.values())


def test_domain_exception_context_mapping() -> None:
    err = ValidationError("bad field", record_id="r1", field="smiles")
    ctx = get_domain_exception_context(err)
    assert ctx is not None
    assert err.record_id == "r1"
    assert err.field == "smiles"
    # None always present
    bare = ValidationError("x")
    assert bare.record_id is None
    assert bare.field is None


def test_schema_violation_record_id_always_present() -> None:
    err = SchemaViolationError("compounds", ["missing smiles"])
    assert err.record_id is None
    assert err.table == "compounds"


def test_pipeline_shutdown_error_nominal() -> None:
    err = PipelineShutdownError(
        "shutdown requested",
        reason=ShutdownReason.SIGNAL_SIGTERM,
    )
    assert isinstance(err, BioETLError)
    assert "shutdown" in str(err).lower() or err.args


def test_storage_compat_exception_classes_are_raiseable() -> None:
    with pytest.raises(BucketNotFoundError) as bucket_exc:
        raise BucketNotFoundError("my-bucket")
    assert bucket_exc.value.bucket == "my-bucket"
    assert bucket_exc.value.get_error_type() == ErrorType.DB_UNAVAILABLE

    with pytest.raises(UploadError) as upload_exc:
        raise UploadError("k", "timeout")
    assert upload_exc.value.key == "k"

    with pytest.raises(BronzeValidationError) as bronze_exc:
        raise BronzeValidationError("bad row", record_index=3)
    assert bronze_exc.value.record_index == 3

    with pytest.raises(CachedBronzeEmptyError) as empty_exc:
        raise CachedBronzeEmptyError("chembl", "activity", "/bronze/path")
    assert empty_exc.value.provider == "chembl"


def test_delta_schema_one_sided_diff_message() -> None:
    msg = _build_schema_validation_message(
        table_path="t",
        expected_columns=["a", "b"],
        actual_columns=[],
        type_mismatches={},
    )
    assert "missing columns" in msg
    err = DeltaSchemaValidationError(
        "t",
        expected_columns=["a"],
        actual_columns=[],
    )
    assert isinstance(err, Exception)
    assert "Schema validation failed" in str(err)


@pytest.mark.parametrize(
    ("provider", "message", "service_name", "expected_provider", "expected_message"),
    [
        (None, None, None, "unknown", "Rate limit exceeded"),
        ("chembl", None, None, "chembl", "chembl"),
        ("chembl", "slow down", None, "chembl", "slow down"),
        ("chembl", None, "chembl-api", "chembl-api", "chembl"),
        (None, "explicit", "svc", "svc", "explicit"),
    ],
)
def test_resolve_rate_limit_params(
    provider: str | None,
    message: str | None,
    service_name: str | None,
    expected_provider: str,
    expected_message: str,
) -> None:
    provider_name, resolved_message, resolved_service = resolve_rate_limit_params(
        provider, message, service_name
    )
    assert provider_name == expected_provider
    assert resolved_message == expected_message
    assert resolved_service == (service_name if service_name is not None else provider)


def test_network_service_constructors() -> None:
    api = ApiError("bad request", status_code=400)
    assert api.status_code == 400
    assert "[400]" in str(api)

    unavailable = ServiceUnavailableError("down", service_name="chembl", status_code=503)
    assert unavailable.service_name == "chembl"

    rate = RateLimitError(provider="chembl", retry_after=1.5)
    assert rate.provider == "chembl"
    assert rate.retry_after == 1.5

    rate2 = RateLimitError(message="too many", service_name="pubchem", retry_after=2.0)
    assert rate2.service_name == "pubchem"

    with pytest.raises(DataValidationError) as dv:
        raise DataValidationError("bad", service_name="x", field="f", value="v")
    assert dv.value.field == "f"
    assert dv.value.get_error_type() == ErrorType.INVALID_DATA


def test_exceptions_package_getattr_contract() -> None:
    import bioetl.domain.exceptions as exc_pkg

    names = list(exc_pkg.__all__)
    assert names
    for name in names:
        value = getattr(exc_pkg, name)
        assert value is not None
    with pytest.raises(AttributeError):
        getattr(exc_pkg, "DefinitelyNotAnExceptionName")


def test_bioetl_domain_error_freezes_nested_context() -> None:
    ctx = {"nested": {"token": "secret"}, "items": [1, {"k": "v"}]}
    err = BioETLDomainError(message="domain fail", context=ctx)
    # Nested mapping is frozen / not the original mutable dict.
    assert err.context is not ctx
    with pytest.raises(TypeError):
        err.context["nested"] = "nope"  # type: ignore[index]
    payload = err.to_dict()
    assert payload["message"] == "domain fail"
    assert isinstance(payload["context"], dict)
