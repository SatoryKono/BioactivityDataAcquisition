"""Capture all detail tables and prove native pagination advances."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("stalled", [False, True])
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
const roots=Object.fromEntries([1,2].map(id=>[id,{
  first(){return this;},scrollIntoViewIfNeeded:async()=>{},waitFor:async()=>{},
  locator:()=>({count:async()=>0}),
  innerText:async()=>`${id}:${states[id]}`,
  evaluate:async()=>({cells:[{text:`row ${states[id]+1}`}],summary:null,scrollers:[]}),
  screenshot:async options=>{const b=Buffer.from('test');fs.writeFileSync(options.path,b);return b;},
  getByRole:(role,{name})=>({count:async()=>id===1?1:0,
    isDisabled:async()=>name==='next page'?states[id]===1:states[id]===0,
    focus:async()=>{active=id;},click:async()=>{states[id]--;}})
}]));
const page={locator:selector=>roots[Number(selector.match(/panel-(\d+)/)[1])],
  keyboard:{press:async()=>{if(!stalled)states[active]++;}},
  waitForTimeout:async()=>{},waitForFunction:async()=>{if(stalled)throw Error('page did not advance');}};
(async()=>{
 try {
  const results=await captureTablePages(page,{dashboard:{uid:'test',firstWindowPanels:[],
    tablePanels:[{id:1,type:'table'},{id:2,type:'table'}]},outputDir:process.argv[2],
    pngEvidence:()=>({bytes:4}),timeout:50});
  console.log(JSON.stringify({results,states}));
 }catch(error){console.log(JSON.stringify({error:error.message}));}
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
        assert evidence["error"] == "page did not advance"
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
