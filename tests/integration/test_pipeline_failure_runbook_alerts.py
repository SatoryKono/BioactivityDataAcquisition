"""Ensure pipeline failure runbook triggers match their Prometheus rules."""

from pathlib import Path
import re

import pytest
import yaml

pytestmark = pytest.mark.integration


def test_pipeline_failure_runbook_trigger_matches_alert_rules() -> None:
    runbook_path = "docs/05-operations/runbooks/pipeline-failure-critical.md"
    trigger = (
        Path(runbook_path)
        .read_text(encoding="utf-8")
        .split("## Trigger\n", 1)[1]
        .split("\n## ", 1)[0]
    )
    documented = re.findall(r"- ALERT: `([^`]+)` — severity: (\w+)\.", trigger)
    payload = yaml.safe_load(
        Path("grafana/prometheus-rules/bioetl_observability.yml").read_text(
            encoding="utf-8"
        )
    )
    rules = {
        rule["alert"]: rule["labels"]["severity"]
        for group in payload["groups"]
        for rule in group["rules"]
        if rule.get("annotations", {}).get("runbook") == runbook_path
    }
    assert len(documented) == 4
    assert dict(documented) == rules
