"""Capture all detail tables and prove native pagination advances."""

from __future__ import annotations

import json
import copy
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "positions,passes",
    [
        ([(0, 0), (100, 0), (0, 100), (100, 100)], True),
        ([], False),
        ([(0, 0), (100, 100)], False),
        ([(0, 0), (100, 0)], False),
    ],
)
def test_scroll_acceptance_requires_complete_two_dimensional_coverage(
    positions, passes
):
    from scripts.ops.observability.grafana.capture_acceptance import _table_page_reasons

    scroller = {
        "clientWidth": 100,
        "clientHeight": 100,
        "scrollWidth": 200,
        "scrollHeight": 200,
        "scrollLeft": 0,
        "scrollTop": 0,
    }
    page = {
        "page": 1,
        "scrollers": [scroller],
        "scrollTiles": [
            {
                "file": f"{x}-{y}.png",
                "sha256": "a" * 64,
                "scrollers": [{**scroller, "scrollLeft": x, "scrollTop": y}],
            }
            for x, y in positions
        ],
    }
    dashboard = {
        "tablePagination": [{"panelId": 1, "status": "COMPLETE", "pages": [page]}]
    }
    assert (not _table_page_reasons(dashboard)) is passes
    if passes:
        wrong = copy.deepcopy(dashboard)
        for tile in wrong["tablePagination"][0]["pages"][0]["scrollTiles"]:
            tile["scrollers"][0]["scrollTop"] = 0
        assert _table_page_reasons(wrong)


@pytest.mark.parametrize("stalled", [False, True, "capture_error"])
def test_detail_and_unpaginated_tables_are_captured(
    tmp_path: Path, stalled: bool
) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    program = r"""
const fs=require('fs');
const {captureTablePages}=require(process.argv[1]);
let active; const states={1:0,2:0};
const stalled=process.argv[3]==='true';
const captureError=process.argv[3]==='capture_error';
const roots=Object.fromEntries([1,2].map(id=>[id,{
  first(){return this;},scrollIntoViewIfNeeded:async()=>{},waitFor:async()=>{},
  locator:()=>({count:async()=>0}),
  innerText:async()=>`${id}:${states[id]}`,
  evaluate:async()=>({cells:[{text:`row ${states[id]+1}`}],summary:null,scrollers:[]}),
  screenshot:async options=>{if(captureError && states[id]===1)throw Error('capture failed');const b=Buffer.from('test');fs.writeFileSync(options.path,b);return b;},
  getByRole:(role,{name})=>({count:async()=>id===1?1:0,
    isDisabled:async()=>name==='next page'?states[id]===1:states[id]===0,
    focus:async()=>{active=id;},click:async()=>{states[id]--;}})
}]));
const page={locator:selector=>roots[Number(selector.match(/panel-(\d+)/)[1])],
  keyboard:{press:async()=>{states[active]++;}},
  waitForTimeout:async()=>{},waitForFunction:async(fn,args,options)=>{
    if(!(options.timeout>0))throw Error('unbounded transition timeout');
    if(stalled)throw Error('page did not advance');}};
(async()=>{
 try {
  const results=await captureTablePages(page,{dashboard:{uid:'test',firstWindowPanels:[],
    tablePanels:[{id:1,type:'table'},{id:2,type:'table'}]},outputDir:process.argv[2],
    pngEvidence:()=>({bytes:4}),timeout:0});
  console.log(JSON.stringify({results,states}));
 }catch(error){console.log(JSON.stringify({error:error.message,states}));}
})();
"""
    result = subprocess.run(
        [
            node,
            "-e",
            program,
            str(
                Path(
                    "scripts/ops/observability/grafana/capture_table_pages.cjs"
                ).resolve()
            ),
            str(tmp_path),
            str(stalled).lower(),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    evidence = json.loads(result.stdout)
    if stalled:
        assert evidence["error"] == (
            "capture failed" if stalled == "capture_error" else "page did not advance"
        )
        assert evidence["states"] == {"1": 0, "2": 0}
        return
    assert [len(t["pages"]) for t in evidence["results"]] == [2, 1]
    assert all(t["status"] == "COMPLETE" for t in evidence["results"])
    assert evidence["states"] == {"1": 0, "2": 0}
    assert len(list(tmp_path.rglob("*.png"))) == 3


def test_projection_includes_tables_inside_collapsed_rows() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    program = """
const {dashboardEntryFromPayload:project}=require(process.argv[1]);
const result=project({uid:'test',panels:[{id:1,type:'row',collapsed:true,panels:[
 {id:2,type:'table',gridPos:{y:50,h:8,w:24,x:0}}]}]});
console.log(JSON.stringify(result.tablePanels));
"""
    result = subprocess.run(
        [
            node,
            "-e",
            program,
            str(
                Path(
                    "scripts/ops/observability/grafana/rerender_grafana_screenshots.cjs"
                ).resolve()
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert [p["id"] for p in json.loads(result.stdout)] == [2]


@pytest.mark.parametrize(
    ("raw", "displayed", "expect", "mapping_type"),
    [
        ("value", "value", "VERIFIED", None),
        ("", "value", "VERIFIED_NO_VALUE_MAPPING", "noValue"),
        (
            "Provider: run_preflight_provider_observation",
            "Provider: saved preflight observation",
            "VERIFIED_VALUE_MAPPING",
            "value",
        ),
        ("12.5", "12.5 s", "VERIFIED_UNIT_FORMAT", "unit"),
        ("unexpected", "value", None, None),
    ],
)
def test_inspector_reads_dialog_and_separates_empty_mapping(
    tmp_path, raw, displayed, expect, mapping_type
):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    program = r"""
const {captureInspectedValues}=require(process.argv[1]);
const raw=process.argv[3];
const displayed=process.argv[4];
const cell={count:async()=>1,evaluate:async()=> displayed,scrollIntoViewIfNeeded:async()=>{},hover:async()=>{},
  getByRole:()=>({count:async()=>1,click:async()=>{}})};
const root={locator:()=>({filter:({hasText})=>{
  if(!hasText.test(displayed) || hasText.test(displayed+'-extra'))throw Error('Non-exact cell lookup');
  return {first:()=>cell};}})};
const pre={waitFor:async()=>{},innerText:async()=>raw};
const dialog={filter(){return this;},locator:selector=>{if(selector!=='pre')throw Error('Not dialog text');return pre;}};
const page={getByRole:role=>role==='dialog'?dialog:{waitFor:async()=>{},click:async()=>{}},
  screenshot:async()=>Buffer.from('test')};
const valueMappings=[{type:'value',raw:'Provider: run_preflight_provider_observation',
  display:'Provider: saved preflight observation'}];
const fieldFormats=[{unit:'s',decimals:null}];
captureInspectedValues(page,root,[{text:displayed,clipped:true,role:'gridcell'}],
 {dir:process.argv[2],index:1,outputDir:process.argv[2],pngEvidence:()=>({}),timeout:100,
  noValue:'value',valueMappings,fieldFormats})
 .then(results=>console.log(JSON.stringify({results})))
 .catch(error=>console.log(JSON.stringify({error:error.message})));
"""
    result = subprocess.run(
        [
            node,
            "-e",
            program,
            str(
                Path(
                    "scripts/ops/observability/grafana/capture_table_pages.cjs"
                ).resolve()
            ),
            str(tmp_path),
            raw,
            displayed,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    evidence = json.loads(result.stdout)
    if expect is None:
        assert "differs" in evidence["error"]
    else:
        value = evidence["results"][0]
        assert value["observed"] == raw
        assert value["text"] == displayed
        assert value["status"] == expect
        if mapping_type == "value":
            assert value["mapping"] == {
                "raw": raw,
                "display": displayed,
                "type": "value",
            }
        elif mapping_type == "unit":
            assert value["mapping"] == {
                "raw": raw,
                "display": displayed,
                "type": "unit",
                "unit": "s",
            }


def test_inspect_runs_before_scroll_restore_and_rejects_unmounted(
    tmp_path: Path,
) -> None:
    """Clipped off-viewport cells must be inspected while still mounted."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    program = r"""
const fs=require('fs');
const path=require('path');
const {captureTablePages}=require(process.argv[1]);
const zoom=require(path.join(path.dirname(process.argv[1]),'native_browser_zoom.cjs'));
zoom.capturePageScreenshot=async(page,options)=>{
  const b=Buffer.from('inspect');fs.writeFileSync(options.path,b);return b;
};
let scrollY=0;
const tileScrollAtShot=[];
zoom.captureElementScreenshot=async(page,root,options)=>{
  tileScrollAtShot.push(scrollY);
  const b=Buffer.from('tile-'+scrollY);fs.writeFileSync(options.path,b);return b;
};
let inspecting=null;
const cellFor=text=>({
  count:async()=>1,evaluate:async()=>text,
  scrollIntoViewIfNeeded:async()=>{scrollY=999;inspecting=text;},
  hover:async()=>{},getByRole:()=>({count:async()=>1,click:async()=>{}}),
});
const root={
  first(){return this;},scrollIntoViewIfNeeded:async()=>{},waitFor:async()=>{},
  innerText:async()=>'panel',
  locator:sel=>{
    if(sel==='[role="grid"]')return{count:async()=>1,nth:()=>({
      evaluate:async(fn,arg)=>{
        if(arg===undefined)return {w:100,h:100,sw:100,sh:200,x:0,y:0};
        scrollY=arg.y;inspecting=null;
      },
    })};
    if(sel==='[role="cell"], [role="gridcell"]')return{filter:({hasText})=>{
      const text=scrollY>0?'hidden-row':'visible-row';
      if(!hasText.test(text))return{first:()=>({count:async()=>0})};
      return{first:()=>cellFor(text)};
    }};
    return{count:async()=>0};
  },
  evaluate:async()=>({
    cells:[{text:scrollY>0?'hidden-row':'visible-row',clipped:true,role:'gridcell'}],
    summary:null,
    scrollers:[{clientWidth:100,clientHeight:100,scrollWidth:100,scrollHeight:200,
      scrollLeft:0,scrollTop:scrollY===999?0:scrollY}],
  }),
  getByRole:()=>({count:async()=>0}),
};
const pre={waitFor:async()=>{},innerText:async()=>inspecting||(scrollY>0?'hidden-row':'visible-row')};
const dialog={filter(){return this;},locator:()=>pre};
const page={
  locator:()=>root,
  waitForTimeout:async()=>{},
  getByRole:role=>role==='dialog'?dialog:{waitFor:async()=>{},click:async()=>{}},
};
(async()=>{
  const results=await captureTablePages(page,{
    dashboard:{uid:'test',firstWindowPanels:[],tablePanels:[{id:1,type:'table'}]},
    outputDir:process.argv[2],pngEvidence:()=>({bytes:4}),timeout:1000,
  });
  console.log(JSON.stringify({results,tileScrollAtShot}));
})().catch(error=>console.log(JSON.stringify({error:error.message})));
"""
    result = subprocess.run(
        [
            node,
            "-e",
            program,
            str(
                Path(
                    "scripts/ops/observability/grafana/capture_table_pages.cjs"
                ).resolve()
            ),
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    evidence = json.loads(result.stdout)
    assert "error" not in evidence, evidence
    table = evidence["results"][0]
    assert table["status"] == "COMPLETE"
    page = table["pages"][0]
    statuses = {item["text"]: item["status"] for item in page["inspectedValues"]}
    assert statuses["visible-row"] == "VERIFIED"
    assert statuses["hidden-row"] == "VERIFIED"
    files = [item["file"] for item in page["inspectedValues"] if item.get("file")]
    assert len(files) == len(set(files))
    assert {Path(f).name for f in files} == {
        "page-1-inspect-1.png",
        "page-1-inspect-2.png",
    }
    # Tile PNGs must be taken at declared scroll offsets, not after Inspect.
    assert 999 not in evidence["tileScrollAtShot"]


def test_cell_not_mounted_retries_on_later_scroll_tile(tmp_path: Path) -> None:
    """CELL_NOT_MOUNTED must not permanently block Inspect on later tiles."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    program = r"""
const fs=require('fs');
const path=require('path');
const {captureInspectedValues,mergeInspected}=require(process.argv[1]);
const zoom=require(path.join(path.dirname(process.argv[1]),'native_browser_zoom.cjs'));
zoom.capturePageScreenshot=async(page,options)=>{
  const b=Buffer.from('inspect');fs.writeFileSync(options.path,b);return b;
};
let mounted=false;
const cell={
  count:async()=>mounted?1:0,evaluate:async()=>'delayed',
  scrollIntoViewIfNeeded:async()=>{},hover:async()=>{},
  getByRole:()=>({count:async()=>1,click:async()=>{}}),
};
const root={locator:()=>({filter:()=>({first:()=>cell})})};
const pre={waitFor:async()=>{},innerText:async()=>'delayed'};
const dialog={filter(){return this;},locator:()=>pre};
const page={getByRole:role=>role==='dialog'?dialog:{waitFor:async()=>{},click:async()=>{}}};
const opts={dir:process.argv[2],index:1,outputDir:process.argv[2],pngEvidence:()=>({}),
  timeout:100,noValue:null,seen:new Set(),inspectCounter:{n:0}};
(async()=>{
  const first=await captureInspectedValues(page,root,[{text:'delayed',clipped:true,role:'gridcell'}],opts);
  mounted=true;
  const second=await captureInspectedValues(page,root,[{text:'delayed',clipped:true,role:'gridcell'}],opts);
  console.log(JSON.stringify({merged:mergeInspected(first,second)}));
})().catch(error=>console.log(JSON.stringify({error:error.message})));
"""
    result = subprocess.run(
        [
            node,
            "-e",
            program,
            str(
                Path(
                    "scripts/ops/observability/grafana/capture_table_pages.cjs"
                ).resolve()
            ),
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    evidence = json.loads(result.stdout)
    assert "error" not in evidence, evidence
    assert evidence["merged"][0]["status"] == "VERIFIED"


@pytest.mark.parametrize(
    "inspect_status,passes",
    [
        ("VERIFIED", True),
        ("CELL_NOT_MOUNTED", False),
        ("INSPECT_UNAVAILABLE", False),
    ],
)
def test_acceptance_rejects_incomplete_inspect(inspect_status, passes):
    from scripts.ops.observability.grafana.capture_acceptance import _table_page_reasons

    dashboard = {
        "tablePagination": [
            {
                "panelId": 1,
                "status": "COMPLETE",
                "pages": [
                    {
                        "page": 1,
                        "scrollers": [],
                        "inspectedValues": [{"text": "x", "status": inspect_status}],
                    }
                ],
            }
        ]
    }
    assert (not _table_page_reasons(dashboard)) is passes
