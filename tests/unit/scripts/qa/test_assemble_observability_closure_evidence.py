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
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa import assemble_observability_closure_evidence as assembler
from scripts.engineering.qa import run_observability_closure_campaign as campaign

pytestmark = pytest.mark.unit


def test_raw_specs_preserve_repeated_kinds() -> None:
    assert assembler._raw_specs(["attempt-result=/a", "attempt-result=/b"]) == [
        ("attempt-result", "/a"),
        ("attempt-result", "/b"),
    ]


def test_assembler_writes_occurrence_bound_promtool_evidence(tmp_path: Path) -> None:
    audit_root = tmp_path / "audit"
    raw_root = audit_root / "evidence" / "raw"
    raw_root.mkdir(parents=True)
    binding = {
        "source_revision": "abc123",
        "source_tree": "tree123",
        "standalone_attempts_sha256": "a" * 64,
        "standalone_attempts": [],
        "online_run_id": "online-1",
        "phase_evidence_sha256": "b" * 64,
    }
    report_path = audit_root / "observability-closure-campaign.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "awaiting_external_evidence",
                "source_revision": "abc123",
                "campaign_binding": binding,
            }
        ),
        encoding="utf-8",
    )
    raw_args: list[str] = []
    for index, phase in enumerate(
        ("check-observability", "check-control-plane", "test-fixtures")
    ):
        path = raw_root / f"promtool-{index}.json"
        path.write_text(
            json.dumps(
                {
                    "phase": phase,
                    "tool_version": "3.13.1",
                    "exit_code": 0,
                    "output": "SUCCESS",
                }
            ),
            encoding="utf-8",
        )
        raw_args.extend(("--raw", f"promtool-output={path}"))
    output = audit_root / "evidence" / "promtool.json"

    exit_code = assembler.main(
        [
            "--campaign-report",
            str(report_path),
            "--category",
            "promtool",
            *raw_args,
            "--summary",
            "rule_file_count=2",
            "--summary",
            "failure_count=0",
            "--output",
            str(output),
            "--tool-version",
            "3.13.1",
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["status"] == "pass"
    assert payload["campaign_binding"] == binding
    assert payload["producer"]["command"][1:3] == [
        "-m",
        campaign.CANONICAL_EVIDENCE_ASSEMBLER,
    ]
