import json
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.services.evidence_location import (
    EvidenceLocationRegistrationOutcome,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationKind,
)
from bioetl.domain.control_plane.run_evidence_location_models import (
    EvidenceLocationLookupCode,
)
from scripts.ops.runtime.register_evidence_roots import _extract_request, main


@pytest.fixture
def mock_service() -> MagicMock:
    service = MagicMock()
    # Mock lookup returning LOCATION_MISSING by default
    lookup_mock = MagicMock()
    lookup_mock.code = EvidenceLocationLookupCode.LOCATION_MISSING
    service.locations.lookup.return_value = lookup_mock

    # Mock register returning registered outcome
    service.register.return_value = EvidenceLocationRegistrationOutcome(
        code="registered", revision="12345"
    )
    return service


@pytest.fixture
def mock_build_service(mock_service: MagicMock) -> Generator[MagicMock, None, None]:
    with patch(
        "scripts.ops.runtime.register_evidence_roots.build_evidence_location_registration_service"
    ) as m:
        m.return_value = (mock_service, MagicMock())
        yield m


@pytest.fixture(autouse=True)
def ensure_logging_for_caplog() -> Generator[None, None, None]:
    import logging

    logger = logging.getLogger("scripts.ops.runtime.register_evidence_roots")
    old_level = logger.level
    logger.setLevel(logging.INFO)
    yield
    logger.setLevel(old_level)


def test_extract_request_direct_payload() -> None:
    payload: dict[str, Any] = {
        "kind": "pipeline",
        "owner": "chembl_assay",
        "run_id": "run-123",
        "runtime_source_id": "src-123",
        "relative_data_root": "a/b/c",
        "root_alias": "default",
        "workflow_run_id": "wf-123",
    }
    request = _extract_request(payload)
    assert request.kind == EvidenceLocationKind.PIPELINE
    assert request.owner == "chembl_assay"
    assert request.run_id == "run-123"
    assert request.runtime_source_id == "src-123"
    assert request.relative_data_root == "a/b/c"
    assert request.root_alias == "default"
    assert request.workflow_run_id == "wf-123"


def test_extract_request_from_identity_block() -> None:
    payload: dict[str, Any] = {
        "identity": {
            "pipeline_name": "chembl_assay",
            "run_id": "run-123",
            "runtime_source_id": "src-123",
        },
        "relative_data_root": "some/path",
    }
    request = _extract_request(payload)
    assert request.kind == EvidenceLocationKind.PIPELINE
    assert request.owner == "chembl_assay"
    assert request.run_id == "run-123"
    assert request.relative_data_root == "some/path"
    assert request.root_alias == DEFAULT_EVIDENCE_ROOT_ALIAS


def test_extract_request_invalid() -> None:
    with pytest.raises(ValueError, match="missing required evidence location fields"):
        _extract_request({"random": "data"})


def test_dry_run_mode_does_not_mutate(
    tmp_path: Path,
    mock_build_service: MagicMock,
    mock_service: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "identity": {
                    "pipeline_name": "test_pipe",
                    "run_id": "run-1",
                    "runtime_source_id": "src-1",
                }
            }
        )
    )

    # Run without --apply
    exit_code = main([str(manifest)])
    assert exit_code == 0

    mock_service.locations.lookup.assert_called_once()
    mock_service.register.assert_not_called()
    assert (
        "Registration receipt: {'PASS': 0, 'FAIL': 0, 'SKIPPED': 0, 'NOT_RUN': 1}"
        in caplog.text
    )


def test_apply_mode_registers_records(
    tmp_path: Path,
    mock_build_service: MagicMock,
    mock_service: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "identity": {
                    "pipeline_name": "test_pipe",
                    "run_id": "run-1",
                    "runtime_source_id": "src-1",
                }
            }
        )
    )

    # Run with --apply
    exit_code = main([str(manifest), "--apply"])
    assert exit_code == 0

    mock_service.register.assert_called_once()
    assert (
        "Registration receipt: {'PASS': 1, 'FAIL': 0, 'SKIPPED': 0, 'NOT_RUN': 0}"
        in caplog.text
    )


def test_conflict_handling_apply(
    tmp_path: Path,
    mock_build_service: MagicMock,
    mock_service: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_service.register.return_value = EvidenceLocationRegistrationOutcome(
        code="conflict", detail="binding_conflict"
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "identity": {
                    "pipeline_name": "test_pipe",
                    "run_id": "run-1",
                }
            }
        )
    )

    exit_code = main([str(manifest), "--apply"])
    assert exit_code == 0

    mock_service.register.assert_called_once()
    assert (
        "Registration receipt: {'PASS': 0, 'FAIL': 0, 'SKIPPED': 1, 'NOT_RUN': 0}"
        in caplog.text
    )


def test_relative_escape_is_rejected(
    mock_build_service: MagicMock,
    mock_service: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    exit_code = main(["../outside-evidence.json"])
    assert exit_code == 1
    mock_build_service.assert_called_once()
    mock_service.register.assert_not_called()
    mock_service.locations.lookup.assert_not_called()
    assert (
        "Registration receipt: {'PASS': 0, 'FAIL': 1, 'SKIPPED': 0, 'NOT_RUN': 0}"
        in caplog.text
    )


def test_invalid_json_handling(
    tmp_path: Path, mock_build_service: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not json")

    exit_code = main([str(bad_file)])
    assert exit_code == 1
    assert (
        "Registration receipt: {'PASS': 0, 'FAIL': 1, 'SKIPPED': 0, 'NOT_RUN': 0}"
        in caplog.text
    )
