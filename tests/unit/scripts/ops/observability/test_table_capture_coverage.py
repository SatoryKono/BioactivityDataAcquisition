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


@pytest.mark.parametrize("raw", ["value", "", "unexpected"])
def test_inspector_reads_dialog_and_separates_empty_mapping(tmp_path, raw):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    program = r"""
const {captureInspectedValues}=require(process.argv[1]);
const raw=process.argv[3];
const cell={count:async()=>1,evaluate:async()=> 'value',scrollIntoViewIfNeeded:async()=>{},hover:async()=>{},
  getByRole:()=>({count:async()=>1,click:async()=>{}})};
const root={locator:()=>({filter:({hasText})=>{
  if(!hasText.test('value') || hasText.test('value-extra'))throw Error('Non-exact cell lookup');
  return {first:()=>cell};}})};
const pre={waitFor:async()=>{},innerText:async()=>raw};
const dialog={filter(){return this;},locator:selector=>{if(selector!=='pre')throw Error('Not dialog text');return pre;}};
const page={getByRole:role=>role==='dialog'?dialog:{waitFor:async()=>{},click:async()=>{}},
  screenshot:async()=>Buffer.from('test')};
captureInspectedValues(page,root,[{text:'value',clipped:true,role:'gridcell'}],
 {dir:process.argv[2],index:1,outputDir:process.argv[2],pngEvidence:()=>({}),timeout:100,noValue:'value'})
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
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    evidence = json.loads(result.stdout)
    if raw == "unexpected":
        assert "differs" in evidence["error"]
    else:
        value = evidence["results"][0]
        assert value["observed"] == raw
        assert value["status"] == ("VERIFIED" if raw else "VERIFIED_NO_VALUE_MAPPING")
