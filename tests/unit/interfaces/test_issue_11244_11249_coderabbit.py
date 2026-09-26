"""Focused coverage for CodeRabbit issues #11244-#11249."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.common.deduplication import build_record_dedup_key
from bioetl.infrastructure.adapters.uniprot.filtering_adapter_mixin import (
    extract_uniprot_accession,
)
from bioetl.interfaces.http.control_plane_identity.severity import (
    _identity_graph_severity,
)
from bioetl.interfaces.http.control_plane_identity.types import (
    _resolve_missing_severity,
)


def test_extract_uniprot_accession_prefers_primary() -> None:
    assert extract_uniprot_accession({"primaryAccession": " P12345 ", "accession": "Q"}) == "P12345"
    assert extract_uniprot_accession({"accession": " Q9 "}) == "Q9"
    assert extract_uniprot_accession({"accession": None, "primaryAccession": None}) is None


def test_dedup_key_none_primary_stays_unkeyed() -> None:
    assert build_record_dedup_key({"id": None}, primary_field="id") is None
    assert build_record_dedup_key({"id": "abc"}, primary_field="id") == "abc"


def test_missing_severity_keeps_explicit_value() -> None:
    assert _resolve_missing_severity("DEGRADED", "SHIPPED") == "DEGRADED"
    assert _resolve_missing_severity(None, "SHIPPED") == "INFO"
    assert _resolve_missing_severity(None, "DEGRADED") == "WARNING"


def test_identity_graph_status_uses_exact_tokens() -> None:
    assert _identity_graph_severity("replay_of_run_id") == "DEGRADED"
    assert _identity_graph_severity("run_id") == "FAILING"
    assert _identity_graph_severity("manifest_id") == "FAILING"


def test_diagnostics_checkpoint_forwards_manifest_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.interfaces.cli.commands import diagnostics as diagnostics_mod

    captured: dict[str, object] = {}

    def _capture(*_args: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(diagnostics_mod, "emit_checkpoint_diagnostics", _capture)
    monkeypatch.setattr(
        diagnostics_mod, "get_observability_diagnostics_bundle", lambda: object()
    )
    assert diagnostics_mod.diagnostics_checkpoint.callback is not None
    diagnostics_mod.diagnostics_checkpoint.callback(
        pipeline="chembl_activity",
        run_id=None,
        manifest_id="manifest-1",
        audit_limit=10,
        output_format="text",
    )
    assert captured["manifest_id"] == "manifest-1"
    assert captured["pipeline"] == "chembl_activity"
