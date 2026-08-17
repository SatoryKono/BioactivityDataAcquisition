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
"""Pure first-window containment helpers from the Playwright render script."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import rerender_grafana_screenshots as rerender


pytestmark = pytest.mark.unit

_SCRIPT = Path(
    "scripts/ops/observability/grafana/rerender_grafana_screenshots.cjs"
).resolve()


def _node_eval(program: str) -> str:
    node_path = rerender._resolve_node_executable()
    if node_path is None:
        pytest.skip("Node.js is unavailable")
    env = os.environ.copy()
    rerender._apply_playwright_runtime_env(env)
    result = subprocess.run(
        [node_path, "-e", program, str(_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        timeout=15,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_select_first_window_panels_skips_rows_and_below_fold() -> None:
    output = _node_eval(
        """
const {
  selectFirstWindowPanels,
  isFirstWindowPanel,
  FIRST_WINDOW_Y,
} = require(process.argv[1]);
const panels = [
  { id: 1, type: "text", gridPos: { x: 0, y: 0, w: 24, h: 4 } },
  { id: 2, type: "row", gridPos: { x: 0, y: 8, w: 24, h: 1 } },
  { id: 3, type: "table", gridPos: { x: 0, y: 11, w: 24, h: 7 } },
  { id: 4, type: "table", gridPos: { x: 0, y: 18, w: 24, h: 5 } },
];
const selected = selectFirstWindowPanels(panels);
if (FIRST_WINDOW_Y !== 18) throw new Error(String(FIRST_WINDOW_Y));
if (selected.map((p) => p.id).join(",") !== "1,3") {
  throw new Error(JSON.stringify(selected.map((p) => p.id)));
}
if (isFirstWindowPanel(panels[1]) || isFirstWindowPanel(panels[3])) {
  throw new Error("row or below-fold selected");
}
console.log("ok");
"""
    )
    assert output == "ok"


def test_evaluate_panel_containment_fails_closed_on_overflow() -> None:
    output = _node_eval(
        """
const { evaluatePanelContainment, evaluateContainmentResults } = require(process.argv[1]);
const base = {
  uid: "bioetl-incident-v1",
  id: 2010,
  title: "Inspect Ranked Suspects",
  type: "table",
  gridPos: { x: 0, y: 11, w: 24, h: 7 },
  clientHeight: 180,
  scrollHeight: 180,
  clientWidth: 1200,
  scrollWidth: 1200,
};
const ok = evaluatePanelContainment(base);
if (ok.status !== "ok") throw new Error(JSON.stringify(ok));
const vertical = evaluatePanelContainment({ ...base, scrollHeight: 220 });
if (vertical.status !== "error" || !vertical.reasons.includes("vertical-overflow")) {
  throw new Error(JSON.stringify(vertical));
}
const exception = evaluatePanelContainment(
  { ...base, scrollHeight: 220 },
  { firstWindowOverflowAllowlist: ["bioetl-incident-v1:2010"] },
);
if (!exception.reasons.includes("forbidden-first-window-overflow-exception")) {
  throw new Error(JSON.stringify(exception));
}
const missing = evaluatePanelContainment({ ...base, missing: true });
if (missing.status !== "error" || !missing.reasons.includes("missing-panel")) {
  throw new Error(JSON.stringify(missing));
}
const batch = evaluateContainmentResults([base, { ...base, scrollWidth: 1400 }]);
if (batch.status !== "error" || batch.overflowCount !== 1) {
  throw new Error(JSON.stringify(batch));
}
console.log("ok");
"""
    )
    assert output == "ok"


def test_containment_manifest_schema_rejects_incomplete_panels() -> None:
    output = _node_eval(
        """
const { validateContainmentManifest } = require(process.argv[1]);
const valid = {
  status: "ok",
  firstWindowY: 18,
  tolerancePx: 2,
  overflowCount: 0,
  panels: [{
    uid: "bioetl-runtime",
    id: 9101,
    title: "Review Runtime Blockers",
    type: "table",
    gridPos: { x: 0, y: 10, w: 12, h: 5 },
    clientHeight: 140,
    scrollHeight: 140,
    clientWidth: 600,
    scrollWidth: 600,
    verticalOverflow: false,
    horizontalOverflow: false,
    status: "ok",
  }],
};
const ok = validateContainmentManifest(valid);
if (ok.status !== "ok") throw new Error(JSON.stringify(ok));
const missing = validateContainmentManifest({
  ...valid,
  panels: [{ id: 1, status: "ok" }],
});
if (missing.status !== "error") throw new Error("incomplete panel accepted");
const widened = validateContainmentManifest({ ...valid, tolerancePx: 8 });
if (widened.status !== "error" || !widened.reasons.includes("invalid-tolerance")) {
  throw new Error(JSON.stringify(widened));
}
console.log(JSON.stringify({ ok: ok.status, missing: missing.reasons.length > 0 }));
"""
    )
    payload = json.loads(output)
    assert payload == {"ok": "ok", "missing": True}


def test_python_preflight_fails_closed_on_recorded_overflow() -> None:
    from scripts.ops.observability.grafana import (
        check_grafana_dashboard_audit_preflight as preflight,
    )

    error = preflight._validate_dashboard_panel_containment(
        "bioetl-incident-v1",
        {
            "panelContainment": {
                "status": "error",
                "panels": [
                    {
                        "uid": "bioetl-incident-v1",
                        "id": 2010,
                        "title": "Inspect Ranked Suspects",
                        "type": "table",
                        "gridPos": {"x": 0, "y": 11, "w": 24, "h": 7},
                        "clientHeight": 180,
                        "scrollHeight": 400,
                        "clientWidth": 1200,
                        "scrollWidth": 1200,
                        "verticalOverflow": True,
                        "horizontalOverflow": False,
                        "status": "error",
                    }
                ],
            }
        },
    )
    assert error is not None
    assert "2010" in error
    assert preflight._validate_dashboard_panel_containment("bioetl-runtime", {}) is None
