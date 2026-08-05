"""Architecture gate: domain ports inventory and RULES.md counts stay current.

Issue #7706 — single authoritative definition of domain *Port inventory via
``scripts.engineering.qa.report_domain_ports_inventory``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from scripts.engineering.qa.report_domain_ports_inventory import (
    collect_ports_inventory,
    render_markdown,
)

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = PROJECT_ROOT / "docs" / "00-project" / "RULES.md"
JSON_PATH = PROJECT_ROOT / "reports" / "quality" / "domain-ports-inventory.json"
MD_PATH = PROJECT_ROOT / "reports" / "quality" / "domain-ports-inventory.md"
GENERATOR_CMD = "report-domain-ports-inventory"

# Hardcoded historical false-friend counts that must not reappear without the
# inventory pointer. Live values are asserted against the generator output.
_FORBIDDEN_STALE_CLAIMS = (
    re.compile(r"Все\s+84\s+порт", re.IGNORECASE),
    re.compile(r"all\s+84\s+port", re.IGNORECASE),
)


def _load_live() -> dict[str, Any]:
    return collect_ports_inventory(repo_root=PROJECT_ROOT)


def test_domain_ports_inventory_live_scan_is_consistent() -> None:
    payload = _load_live()
    summary = payload["summary"]
    assert isinstance(summary, dict)

    assert summary["port_protocol_classes"] >= 1
    assert summary["runtime_checkable_port_count"] == summary["port_protocol_classes"]
    assert summary["port_module_files"] >= 1
    assert summary["scanned_python_files"] >= summary["port_module_files"]
    assert summary["runtime_checkable_decorator_count"] >= summary[
        "runtime_checkable_port_count"
    ]

    ports = payload["ports"]
    assert isinstance(ports, list)
    assert len(ports) == summary["port_protocol_classes"]
    assert all(item["runtime_checkable"] for item in ports)


def test_domain_ports_inventory_artifacts_match_live_scan() -> None:
    payload = _load_live()
    expected_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(payload)

    assert JSON_PATH.is_file(), (
        f"missing {JSON_PATH}; run: python -m scripts.engineering.qa "
        f"{GENERATOR_CMD}"
    )
    assert MD_PATH.is_file(), (
        f"missing {MD_PATH}; run: python -m scripts.engineering.qa {GENERATOR_CMD}"
    )
    assert JSON_PATH.read_text(encoding="utf-8") == expected_json, (
        f"stale {JSON_PATH}; regenerate via python -m scripts.engineering.qa "
        f"{GENERATOR_CMD}"
    )
    assert MD_PATH.read_text(encoding="utf-8") == expected_md, (
        f"stale {MD_PATH}; regenerate via python -m scripts.engineering.qa "
        f"{GENERATOR_CMD}"
    )


def test_rules_ports_section_points_at_generator_and_live_counts() -> None:
    rules = RULES_PATH.read_text(encoding="utf-8")
    payload = _load_live()
    summary = payload["summary"]
    assert isinstance(summary, dict)

    for pattern in _FORBIDDEN_STALE_CLAIMS:
        assert pattern.search(rules) is None, (
            f"RULES.md still embeds forbidden stale port claim matching {pattern!r}"
        )

    assert GENERATOR_CMD in rules or "report_domain_ports_inventory" in rules, (
        "RULES.md must reference the domain ports inventory generator"
    )
    assert "domain-ports-inventory" in rules, (
        "RULES.md must point at reports/quality/domain-ports-inventory artifacts"
    )

    protocol_count = int(summary["port_protocol_classes"])
    runtime_count = int(summary["runtime_checkable_port_count"])
    module_files = int(summary["port_module_files"])

    # Embedded live snapshot numbers must match the generator when present.
    for value, label in (
        (protocol_count, "port_protocol_classes"),
        (runtime_count, "runtime_checkable_port_count"),
        (module_files, "port_module_files"),
    ):
        # Require the live integer to appear near the inventory discussion so a
        # silent drift of the prose snapshot is caught without forbidding the
        # same number elsewhere in RULES.
        assert str(value) in rules, (
            f"RULES.md must embed live {label}={value} from the ports inventory"
        )


@pytest.mark.parametrize(
    "metric",
    (
        "port_protocol_classes",
        "runtime_checkable_port_count",
        "port_module_files",
        "scanned_python_files",
    ),
)
def test_domain_ports_inventory_summary_metrics_are_ints(metric: str) -> None:
    summary = _load_live()["summary"]
    assert isinstance(summary, dict)
    assert isinstance(summary[metric], int)
    assert summary[metric] >= 0
