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


def test_browser_cleanup_preserves_ownership_and_disposal_order() -> None:
    output = _node_eval("""
const {closeCaptureBrowser} = require(process.argv[1]);
(async () => {
  const calls = [];
  const resource = (label) => ({close: async () => calls.push(label)});
  const contextBundle = {api: {dispose: async () => calls.push('api')}};
  await closeCaptureBrowser({contextBundle, context: resource('context'),
    browser: resource('browser')});
  await closeCaptureBrowser({contextBundle, context: resource('owned-context'),
    native: resource('native')});
  await closeCaptureBrowser({browser: resource('partial-browser')});
  await closeCaptureBrowser({});
  console.log(JSON.stringify(calls));
})().catch(error => {console.error(error); process.exitCode = 1;});
""")
    assert json.loads(output) == [
        "api",
        "context",
        "browser",
        "api",
        "native",
        "partial-browser",
    ]


def test_scroll_typography_requires_every_panel_and_retains_failed_frames() -> None:
    output = _node_eval("""
const {mergeTypographyObservations: merge} = require(process.argv[1]);
const required = [{id:1},{id:2}];
const first = {panels:[{id:1}],violations:[]};
const second = {panels:[{id:2}],violations:[]};
const failed = {panels:[{id:1}],violations:[{id:1,reason:'font below floor'}]};
console.log(JSON.stringify([merge(required,[first,second]),merge(required,[first]),
  merge(required,[failed,first,second]),merge(required,[])]));
""")
    complete, missing, failed, empty = json.loads(output)
    assert complete["status"] == "ok"
    assert complete["checkedPanelCount"] == 2
    assert missing["status"] == empty["status"] == failed["status"] == "error"
    assert failed["violations"] == [{"id": 1, "reason": "font below floor"}]
    assert missing["violations"][0]["id"] == 2


def test_text_contrast_composites_alpha_and_preserves_unmeasured_gradients() -> None:
    output = _node_eval(
        """
const {accessibilityMeasurementsFromDom} = require(process.argv[1]);
const base = {opacity:'1',filter:'none',mixBlendMode:'normal',backgroundImage:'none',
  backgroundColor:'rgb(255, 255, 255)',color:'rgb(0, 0, 0)',fontSize:'16px',fontWeight:'400',
  visibility:'visible',display:'block',textOverflow:'clip',overflowX:'visible',overflowY:'visible'};
const make = (style) => ({childNodes:[{nodeType:3,textContent:'Example'}],
  getBoundingClientRect:()=>({x:0,y:0,width:100,height:24}),style:{...base,...style},parentElement:null});
const black=make({});
const same=make({color:'rgb(255, 255, 255)'});
const alpha=make({color:'rgba(0, 0, 0, 0.5)'});
const gradient=make({backgroundImage:'linear-gradient(white, black)'});
global.document={querySelectorAll:()=>[{dataset:{vizPanelKey:'panel-1'},querySelectorAll:()=>[black,same,alpha,gradient]}]};
global.getComputedStyle=(el)=>el.style;
global.window={devicePixelRatio:1}; global.innerWidth=1366; global.innerHeight=768;
global.location={href:'http://localhost/test'};
console.log(JSON.stringify(accessibilityMeasurementsFromDom().pairs));
"""
    )
    pairs = json.loads(output)
    assert pairs[0]["ratio"] == pytest.approx(21)
    assert pairs[0]["status"] == "PASS"
    assert pairs[1]["ratio"] == pytest.approx(1)
    assert pairs[1]["status"] == "FAIL"
    assert pairs[2]["ratio"] == pytest.approx(3.976653024912438)
    assert pairs[2]["status"] == "FAIL"
    assert pairs[3]["ratio"] is None
    assert pairs[3]["status"] == "NOT_VERIFIABLE"


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


def test_pick_best_scroller_prefers_overflow_auto_child() -> None:
    """#9250: panel-content 110/110 must not hide a nested overflow:auto 191/94."""
    output = _node_eval(
        """
const {
  pickBestScrollerCandidate,
  evaluatePanelContainment,
  isScrollableOverflow,
} = require(process.argv[1]);
const panelContent = {
  selector: "panel-content",
  clientHeight: 110,
  scrollHeight: 110,
  clientWidth: 1032,
  scrollWidth: 1032,
};
const innerAuto = {
  selector: "overflow:auto/auto",
  clientHeight: 94,
  scrollHeight: 191,
  clientWidth: 1016,
  scrollWidth: 1016,
};
const picked = pickBestScrollerCandidate([panelContent, innerAuto]);
if (picked.selector !== "overflow:auto/auto") {
  throw new Error(JSON.stringify(picked));
}
if (!isScrollableOverflow("auto") || isScrollableOverflow("hidden")) {
  throw new Error("overflow keyword map");
}
const measured = evaluatePanelContainment({
  uid: "bioetl-run-explorer-v1",
  id: 1,
  title: "Understand Run Scope",
  type: "text",
  gridPos: { x: 0, y: 4, w: 24, h: 4 },
  ...innerAuto,
});
if (measured.status !== "error" || !measured.reasons.includes("vertical-overflow")) {
  throw new Error(JSON.stringify(measured));
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


def test_actual_fold_cannot_pass_with_internal_fit_only() -> None:
    output = _node_eval("""
const {evaluatePanelContainment} = require(process.argv[1]);
const panel={uid:'test',id:1,type:'table',gridPos:{y:11},clientHeight:200,scrollHeight:200,
 clientWidth:600,scrollWidth:600,bbox:{x:0,y:602,width:600,height:266},fold:768,enforceFold:true};
console.log(JSON.stringify(evaluatePanelContainment(panel)));
""")
    result = json.loads(output)
    assert result["status"] == "error"
    assert "outside-first-viewport" in result["reasons"]


def test_graphic_contrast_does_not_promote_canvas_or_translucency() -> None:
    output = _node_eval("""
const {graphicsMeasurementsFromDom} = require(process.argv[1]);
const base={opacity:'1',fillOpacity:'1',strokeOpacity:'1',filter:'none',backgroundImage:'none',
 backgroundColor:'rgb(255, 255, 255)',fill:'rgb(0, 0, 0)',stroke:'none',display:'block',visibility:'visible'};
const control={getAttribute:()=> 'Inspect',textContent:'Inspect',matches:()=>false};
const make=(tag,style={})=>({tagName:tag,style:{...base,...style},parentElement:{style:base,parentElement:null},
 getBoundingClientRect:()=>({x:0,y:0,width:20,height:20}),closest:()=>control});
const shapes=[make('path'),make('path',{fill:'rgb(220, 220, 220)'}),make('canvas'),make('path',{opacity:'0.5'})];
global.document={querySelectorAll:()=>[{dataset:{vizPanelKey:'panel-1'},querySelectorAll:()=>shapes}]};
global.getComputedStyle=(el)=>el.style;
console.log(JSON.stringify(graphicsMeasurementsFromDom()));
""")
    result = json.loads(output)
    assert result["pairs"][0]["ratio"] == pytest.approx(21)
    assert result["pairs"][0]["status"] == "PASS"
    assert result["pairs"][1]["status"] == "FAIL"
    assert result["pairs"][2]["status"] == "NOT_VERIFIABLE"
    assert result["canvases"][0]["status"] == "NOT_VERIFIABLE"


def test_native_gradient_uses_worst_case_bound_and_svg_composites_alpha() -> None:
    output = _node_eval("""
const {accessibilityMeasurementsFromDom,graphicsMeasurementsFromDom}=require(process.argv[1]);
const base={opacity:'1',filter:'none',mixBlendMode:'normal',backgroundImage:'none',backgroundColor:'rgb(0, 0, 0)',
 color:'rgb(247, 247, 247)',fontSize:'24px',fontWeight:'400',display:'block',visibility:'visible',fillOpacity:'1',strokeOpacity:'1'};
const el={childNodes:[{nodeType:3,textContent:'UNKNOWN'}],parentElement:null,tagName:'SPAN',
 getBoundingClientRect:()=>({x:0,y:0,width:120,height:30}),style:{...base,backgroundImage:'linear-gradient(120deg, rgb(90, 90, 90), rgb(115, 115, 115))'}};
global.getComputedStyle=e=>e.style;global.window={devicePixelRatio:1};global.innerWidth=1366;global.innerHeight=768;global.location={href:'http://test/'};
global.document={querySelectorAll:()=>[{dataset:{vizPanelKey:'panel-1'},querySelectorAll:()=>[el]}]};
const text=accessibilityMeasurementsFromDom().pairs[0];
const shape={tagName:'path',getBoundingClientRect:el.getBoundingClientRect,parentElement:{style:base,parentElement:null},
 closest:()=>null,style:{...base,stroke:'none',fill:'rgba(255, 255, 255, 0.5)'}};
global.document={querySelectorAll:()=>[{dataset:{vizPanelKey:'panel-1'},querySelectorAll:()=>[shape]}]};
console.log(JSON.stringify({text,graphic:graphicsMeasurementsFromDom().pairs[0]}));
""")
    result = json.loads(output)
    assert result["text"]["background"] == [115, 115, 115]
    assert result["text"]["status"] == "PASS"
    assert result["graphic"]["effectiveForeground"] == [127.5, 127.5, 127.5]
    assert result["graphic"]["ratio"] == pytest.approx(5.280822809644651)


def test_canvas_contrast_uses_observed_paint_and_records_raster_alpha() -> None:
    """Antialiasing is evidence, while missing/composited paint cannot pass."""
    output = _node_eval(
        r"""
const {canvasEvidenceFromDom}=require(require('node:path').join(require('node:path').dirname(process.argv[1]),'capture_canvas_evidence.cjs'));
const pixels=new Uint8ClampedArray(20*20*4);
const index=(5*20+5)*4;pixels.set([0,0,0,96],index);
const calls=[{method:'fillText',text:'X',foreground:'#000000',font:'12px sans-serif',alpha:1,composition:'source-over',bounds:{x:4,y:4,width:4,height:4}}];
const canvas={width:20,height:20,parentElement:null,getBoundingClientRect:()=>({x:0,y:0,width:20,height:20}),
 closest:()=>({dataset:{vizPanelKey:'panel-1'}}),getContext:()=>({getImageData:()=>({data:pixels})}),toDataURL:()=>''};
global.document={querySelectorAll:()=>[canvas]};
global.window={__bioetlCanvasEvidence:new Map([[canvas,new Map(calls.map((x,i)=>[i,x]))]])};
global.getComputedStyle=()=>({backgroundColor:'rgb(255, 255, 255)',backgroundImage:'none',opacity:'1',filter:'none'});
const pair=canvasEvidenceFromDom()[0].measurements.pairs.text[0];
if(pair.ratio!==21||pair.status!=='PASS'||pair.pixelWitness.foreground.rasterAlpha!==96/255)throw Error(JSON.stringify(pair));
pixels.fill(0);
const absent=canvasEvidenceFromDom()[0].measurements.pairs.text[0];
if(absent.ratio!==null||absent.status!=='NOT_VERIFIABLE')throw Error('Absent pixels passed');
calls[0].alpha=.5;
const unsupported=canvasEvidenceFromDom()[0].measurements.pairs.text[0];
if(unsupported.ratio!==null||unsupported.status!=='NOT_VERIFIABLE')throw Error('Unsupported paint passed');
process.stdout.write('ok');
"""
    )
    assert output == "ok"
