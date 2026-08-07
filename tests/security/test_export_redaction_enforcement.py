"""Security regressions for governed export redaction."""

from __future__ import annotations

import pyarrow as pa
import pytest

from bioetl.application.services.export_lineage.export_execution import (
    apply_redaction_policy,
)
from bioetl.application.services.export_lineage.export_models import ExportOptions

pytestmark = [pytest.mark.security, pytest.mark.unit]


def test_unprivileged_export_removes_all_sensitive_columns() -> None:
    table = pa.table(
        {
            "entity_id": ["1"],
            "raw_payload": ["private-record"],
            "api_token": ["secret-token"],
            "credential_blob": ["secret-credential"],
        }
    )

    redacted, columns = apply_redaction_policy(
        table=table,
        options=ExportOptions(role="viewer"),
    )

    assert isinstance(redacted, pa.Table)
    assert redacted.column_names == ["entity_id"]
    assert columns == ("raw_payload", "api_token", "credential_blob")


def test_unprivileged_export_cannot_disable_redaction() -> None:
    table = pa.table({"entity_id": ["1"], "raw_payload": ["private-record"]})

    with pytest.raises(PermissionError, match="cannot export raw sensitive fields"):
        apply_redaction_policy(
            table=table,
            options=ExportOptions(role="viewer", redaction_profile="none"),
        )
