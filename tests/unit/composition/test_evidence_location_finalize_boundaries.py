"""Finalize hooks keep run identity and diagnostics separate from processing status."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.composition import evidence_location_registration as subject

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("workflow", [False, True])
def test_finalize_verifier_preserves_owner_and_workflow_identity(monkeypatch, workflow):
    service = Mock()
    expected = subject.EvidenceLocationVerifyOutcome(code="ok", verdict="OK")
    service.record_verify_observation.return_value = expected
    binding = SimpleNamespace(
        skip_reason=None,
        runtime_source_id="b" * 64,
        relative_data_root="fixture/run",
        root_alias="dashboard_data",
    )
    monkeypatch.setattr(
        subject,
        "build_evidence_location_registration_service",
        lambda settings: (service, binding),
    )
    settings = object()
    if workflow:
        actual = subject.verify_workflow_run_location(
            workflow_name="workflow", workflow_run_id="parent", settings=settings
        )
    else:
        actual = subject.verify_pipeline_run_location(
            pipeline_name="pipeline",
            run_id="child",
            workflow_run_id="parent",
            settings=settings,
        )
    assert actual is expected
    request = service.record_verify_observation.call_args.args[0]
    assert request.owner == ("workflow" if workflow else "pipeline")
    assert request.run_id == ("parent" if workflow else "child")
    assert request.workflow_run_id == (None if workflow else "parent")
    assert request.relative_data_root == "fixture/run"


def test_unbound_finalize_does_not_publish_observation(monkeypatch):
    service = Mock()
    binding = SimpleNamespace(skip_reason=None, runtime_source_id=None)
    monkeypatch.setattr(
        subject,
        "build_evidence_location_registration_service",
        lambda settings: (service, binding),
    )
    assert (
        subject.verify_pipeline_run_location(
            pipeline_name="pipeline",
            run_id="child",
            workflow_run_id=None,
            settings=object(),
        )
        is None
    )
    service.record_verify_observation.assert_not_called()


def test_finalize_callback_keeps_failed_processing_status(monkeypatch):
    verify = Mock(
        return_value=subject.EvidenceLocationVerifyOutcome(
            code="binding_mismatch", verdict="ERROR"
        )
    )
    monkeypatch.setattr(subject, "verify_pipeline_run_location", verify)
    result = SimpleNamespace(
        pipeline_name="pipeline", run_id="child", processing_status="failed"
    )
    settings = object()
    hook = subject.bind_pipeline_run_location_verifier(settings)
    hook(result, SimpleNamespace(workflow_run_id="parent"))
    assert verify.call_args.kwargs["workflow_run_id"] == "parent"
    assert verify.call_args.kwargs["run_id"] == "child"
    assert result.processing_status == "failed"


@pytest.mark.parametrize("custom_root", [False, True])
def test_builder_uses_report_root_and_trusted_dashboard_alias(
    monkeypatch, tmp_path, custom_root
):
    root = tmp_path / "run-reports" if custom_root else None
    binding = SimpleNamespace(report_root=root, alias_base=tmp_path / "trusted")
    monkeypatch.setattr(
        subject, "build_evidence_location_binding_context", lambda settings: binding
    )
    registry = Mock()
    monkeypatch.setattr(subject, "default_evidence_root_alias_registry", registry)
    factory = Mock()
    monkeypatch.setattr(subject, "FileEvidenceLocationStore", factory)
    service, actual = subject.build_evidence_location_binding_service(object())
    assert actual is binding and service.locations is factory.return_value
    factory.assert_called_once_with(
        report_root=root if custom_root else Path("reports") / "run-reports"
    )
    registry.assert_called_once_with(dashboard_data_root=binding.alias_base)
