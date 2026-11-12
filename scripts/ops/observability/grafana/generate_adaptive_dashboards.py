"""Generate an explicitly selected local adaptive profile; retain native fallbacks."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import yaml

from scripts.ops.observability.grafana._audit_presentation import (
    enable_adaptive_catalog,
)

ROOT = Path(__file__).resolve().parents[4]


def project(source: dict) -> dict:
    """Preserve queries and identity; adapt the catalog and prioritize the verdict."""
    result = deepcopy(source)
    if result.get("uid") == "bioetl-run-explorer-v1":
        enable_adaptive_catalog(result)
    if result.get("uid") == "bioetl-overview-v2":
        # Keep the main answer first when Grafana stacks columns at 200%.
        # Give the status stack one additional column so docked-menu desktop
        # widths retain complete status words. Scope and queries are unchanged.
        panels = {panel["id"]: panel for panel in result["panels"]}
        for panel_id in (9604, 9603, 9300):
            panels[panel_id]["gridPos"]["x"] = 0
            panels[panel_id]["gridPos"]["w"] = 10
        for panel_id in (99, 9002):
            panels[panel_id]["gridPos"].update(x=10, w=14)
    return result


def generate(*, check: bool = False) -> int:
    """Project the optional profile behind the existing navigation renderer."""
    outputs: dict[Path, str] = {}
    hashes = {}
    for path in sorted((ROOT / "grafana/dashboards").glob("*.json")):
        raw = path.read_text(encoding="utf-8")
        hashes[path.name] = hashlib.sha256(raw.encode()).hexdigest()
        outputs[ROOT / "grafana/dashboards-adaptive" / path.name] = (
            json.dumps(project(json.loads(raw)), ensure_ascii=False, indent=2) + "\n"
        )
    provider = yaml.safe_load(
        (ROOT / "grafana/provisioning/dashboards/bioetl.yaml").read_text()
    )
    for item in provider["providers"]:
        item["options"]["path"] = item["options"]["path"].replace(
            "/var/lib/grafana/dashboards/", "/var/lib/grafana/dashboards-adaptive/"
        )
    outputs[ROOT / "grafana/provisioning/dashboards-adaptive/bioetl.yaml"] = (
        yaml.safe_dump(provider, sort_keys=False)
    )
    bundle = ROOT / "grafana/plugins/bioetl-selectorshell-panel/dist-adaptive"
    outputs[ROOT / "grafana/dashboards-adaptive/profile.json"] = (
        json.dumps(
            {
                "profile": "adaptive-table-v1",
                "selection": "explicit_local_only",
                "native_fallback": "grafana/dashboards",
                "canonical_sha256": hashes,
                "plugin_version": json.loads((bundle / "plugin.json").read_text())[
                    "info"
                ]["version"],
                "module_sha256": hashlib.sha256(
                    (bundle / "module.js").read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    drift = []
    for path, content in outputs.items():
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                drift.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if drift:
        print("Adaptive profile drift: " + ", ".join(drift))
        return 1
    print(
        "Adaptive profile current"
        if check
        else "Generated explicit adaptive profile; native fallbacks unchanged"
    )
    return 0
