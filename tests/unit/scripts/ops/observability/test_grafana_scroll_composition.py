"""Verify that exported scroll captures preserve every document row."""

import json
from pathlib import Path
import subprocess

import pytest

pytestmark = pytest.mark.unit


REPO_ROOT = Path(__file__).resolve().parents[5]
COMPOSITOR = REPO_ROOT / "scripts/ops/observability/grafana/capture_scroll_surface.cjs"


@pytest.mark.parametrize("scale", [1, 1.25, 2])
@pytest.mark.parametrize("client_height", [599.6, 600.4, 700.4])
def test_capture_reaches_fractional_scroll_limit(tmp_path, scale, client_height):
    """Run the actual DOM measurement and loop against a fractional scroll range."""
    script = r"""
const fs=require('node:fs'), path=require('node:path');
const [modulePath,directory]=process.argv.slice(1);
const scale=Number(process.argv[3]), height=Number(process.argv[4]);
global.innerHeight=916; global.innerWidth=1366; global.devicePixelRatio=scale;
let scrollTop=0;
const maximum=1800-height;
const el={
  dataset:{},clientHeight:Math.round(height),scrollHeight:1800,
  getBoundingClientRect:()=>({top:232,height,width:1366}),
  querySelectorAll:selector=>selector==='[data-viz-panel-key]' ? [{},{}] : [],
  get scrollTop(){return scrollTop;},
  set scrollTop(value){scrollTop=Math.min(maximum,Math.max(0,value));},
};
global.document={
  querySelectorAll:selector=>selector==='*' ? [el] : [],
  querySelector:()=>el,scrollingElement:el,
};
const native=require(path.join(path.dirname(modulePath),'native_browser_zoom.cjs'));
native.capturePageScreenshot=async(_page,options)=>{
  const bytes=Buffer.from('synthetic viewport');fs.writeFileSync(options.path,bytes);return bytes;
};
const {captureScrollSurface}=require(modulePath);
const page={
  evaluate:async(fn,arg)=>fn(arg),waitForTimeout:async()=>{},
  context:()=>({newPage:async()=>({
    evaluate:async()=>Buffer.from('synthetic composite').toString('base64'),close:async()=>{},
  })}),
};
captureScrollSurface(page,{
  filePath:path.join(directory,'dashboard.png'),timeout:1000,
  pngEvidence:()=>({width:Math.round(1366*scale),height:Math.round(916*scale)}),
  measure:async()=>({}),
}).then(result=>{
  if(height>684)throw new Error('Accepted an incomplete container clipped below the viewport');
  const positions=result.tiles.map(tile=>tile.scrollTop);
  if(positions.at(-1)!==maximum)throw new Error(`Missing actual scroll limit: ${positions}`);
  if(new Set(positions).size!==positions.length)throw new Error('Captured a stalled duplicate');
  if(result.surface.maxScrollTop!==maximum)throw new Error('Actual scroll range not measured');
  if(Math.abs(result.surface.clientHeight-height)>1e-9)throw new Error('Rounded client geometry');
  let covered=0;
  result.composition.slices.forEach((slice,i)=>{
    if(slice.destinationY!==covered)throw new Error('Gap or overwritten pixels');
    if(slice.sourceY+slice.height>Math.round((232+height)*scale))
      throw new Error('Copied pixels below the scroll container');
    if(i>0 && slice.sourceY<Math.ceil(232*scale))throw new Error('Copied sticky chrome');
    covered+=slice.height;
  });
  if(covered!==Math.round(2032*scale))throw new Error('Incomplete physical document');
  console.log(JSON.stringify({clipped:false,covered,last:positions.at(-1)}));
}).catch(error=>{
  if(height>684 && error.message.includes('made no progress')){console.log(JSON.stringify({clipped:true}));return;}
  console.error(error);process.exitCode=1;
});
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(COMPOSITOR),
            str(tmp_path),
            str(scale),
            str(client_height),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    proof = json.loads(result.stdout)
    if client_height > 684:
        assert proof == {"clipped": True}
    else:
        assert proof["clipped"] is False
        assert proof["covered"] == int(2032 * scale + 0.5)
        assert proof["last"] == pytest.approx(1800 - client_height)


@pytest.mark.parametrize("scale", [1.25, 1.5, 1.75])
def test_fractional_zoom_preserves_complete_bounded_document(scale):
    script = r"""
const {compositionSlices} = require(process.argv[1]);
const scale=Number(process.argv[2]);
const surface={top:232,stickyBottom:232,clientHeight:685,scrollHeight:1306,scale};
const tiles=[0,621].map(scrollTop=>({scrollTop,height:Math.round(917*scale)}));
const plan=compositionSlices(surface,tiles);
const expectedHeight=Math.round(1538*scale);
if(plan.canvasHeight!==expectedHeight) throw new Error('Incorrect document height');
let covered=0;
plan.slices.forEach((slice,i)=>{
  if(slice.destinationY!==covered) throw new Error('Gap or overwritten pixels');
  if(slice.sourceY<0 || slice.sourceY+slice.height>Math.round(917*scale))
    throw new Error('Source rectangle exceeds scroll container');
  if(i>0 && slice.sourceY<Math.ceil(232*scale)) throw new Error('Sticky chrome included');
  covered+=slice.height;
});
if(covered!==expectedHeight) throw new Error('Missing physical document pixels');
console.log(JSON.stringify({height:plan.canvasHeight,covered,tiles:plan.slices.length}));
"""
    result = subprocess.run(
        ["node", "-e", script, str(COMPOSITOR), str(scale)],
        check=True,
        capture_output=True,
        text=True,
    )
    proof = json.loads(result.stdout)
    assert proof == {
        "height": int(1538 * scale + 0.5),
        "covered": int(1538 * scale + 0.5),
        "tiles": 2,
    }


@pytest.mark.parametrize("scale", [1, 2])
@pytest.mark.parametrize("offsets", [[0, 218], [0, 620, 1240, 1418]])
def test_composition_preserves_document_rows_without_toolbar_shadow(scale, offsets):
    """Later tiles must neither replace content with chrome nor omit rows."""
    script = r"""
const {compositionSlices} = require(process.argv[1]);
const scale = Number(process.argv[2]);
const offsets = JSON.parse(process.argv[3]);
const surface = {top:232, stickyBottom:232, clientHeight:684, scrollHeight:684+offsets.at(-1), scale};
const tiles = offsets.map(scrollTop => ({scrollTop, height:916*scale}));
const plan = compositionSlices(surface, tiles);
const rows = [];
plan.slices.forEach((slice, i) => {
  if (rows.length !== slice.destinationY) throw new Error('gap or overwritten rows');
  for (let y=slice.sourceY; y<slice.sourceY+slice.height; y++) {
    rows.push(i>0 && y<264*scale ? -1 : y+offsets[i]*scale);
  }
});
if (rows.length !== (916+offsets.at(-1))*scale) throw new Error('incorrect document height');
rows.forEach((value, y) => {if (value!==y) throw new Error(`corrupted document row ${y}: ${value}`);});
console.log(JSON.stringify({height:plan.canvasHeight,rows:rows.length,first:rows[0],last:rows.at(-1)}));
"""
    result = subprocess.run(
        ["node", "-e", script, str(COMPOSITOR), str(scale), json.dumps(offsets)],
        check=True,
        capture_output=True,
        text=True,
    )
    height = (916 + offsets[-1]) * scale
    assert json.loads(result.stdout) == {
        "height": height,
        "rows": height,
        "first": 0,
        "last": height - 1,
    }


def test_incomplete_capture_is_rejected():
    script = r"""
const {compositionSlices} = require(process.argv[1]);
try {
  compositionSlices({top:232,stickyBottom:232,clientHeight:684,scrollHeight:902,scale:1},
    [{scrollTop:0,height:916}]);
} catch(error) {
  if (error.message.includes('incomplete document')) {console.log(JSON.stringify({rejected:true,reason:error.message}));process.exit(0);}
  throw error;
}
throw new Error('Incomplete capture was accepted');
"""
    result = subprocess.run(
        ["node", "-e", script, str(COMPOSITOR)],
        check=True,
        capture_output=True,
        text=True,
    )
    proof = json.loads(result.stdout)
    assert proof["rejected"] is True
    assert "incomplete document" in proof["reason"]


@pytest.mark.parametrize("scale", [1, 2])
def test_composition_excludes_pixels_below_scroll_container(scale):
    script = r"""
const {compositionSlices} = require(process.argv[1]);
const scale = Number(process.argv[2]);
const offsets = [0,536,1072,1200];
const surface = {top:232,stickyBottom:232,clientHeight:600,scrollHeight:1800,scale};
const plan = compositionSlices(surface, offsets.map(scrollTop=>({scrollTop,height:916*scale})));
const rows = [];
plan.slices.forEach((slice,i)=>{
  for(let y=slice.sourceY;y<slice.sourceY+slice.height;y++) {
    rows.push(y>=832*scale || (i>0 && y<264*scale) ? -1 : y+offsets[i]*scale);
  }
});
if(rows.length!==2032*scale) throw new Error('Incomplete dashboard');
rows.forEach((value,y)=>{if(value!==y) throw new Error(`Background or shadow replaced row ${y}`);});
console.log(JSON.stringify({height:plan.canvasHeight,rows:rows.length,first:rows[0],last:rows.at(-1)}));
"""
    result = subprocess.run(
        ["node", "-e", script, str(COMPOSITOR), str(scale)],
        check=True,
        capture_output=True,
        text=True,
    )
    height = 2032 * scale
    assert json.loads(result.stdout) == {
        "height": height,
        "rows": height,
        "first": 0,
        "last": height - 1,
    }


@pytest.mark.parametrize("remainder", [1, 2])
@pytest.mark.parametrize("scale", [1, 2])
def test_capture_scrolls_to_last_document_pixel(tmp_path, remainder, scale):
    """Exercise the capture loop with a final one/two-pixel scroll step."""
    script = r"""
const fs = require('node:fs');
const path = require('node:path');
const modulePath = process.argv[1], directory = process.argv[2];
const remainder = Number(process.argv[3]), scale = Number(process.argv[4]);
const surface = {top:232,stickyBottom:232,clientHeight:684,scrollHeight:1304+remainder,scale};
const native = require(path.join(path.dirname(modulePath),'native_browser_zoom.cjs'));
native.capturePageScreenshot = async (_page,options)=>{
  const bytes=Buffer.from('synthetic viewport');
  fs.writeFileSync(options.path,bytes);
  return bytes;
};
const {captureScrollSurface} = require(modulePath);
let scrollTop=0;
const page = {
  evaluate: async (fn,arg)=>{
    const code=fn.toString();
    if(code.includes('const candidates')) return surface;
    if(code.includes('el.scrollTop=y')) {
      scrollTop=Math.min(arg,surface.scrollHeight-surface.clientHeight);
      return scrollTop;
    }
    if(code.includes('delete el.dataset')) {scrollTop=0;return;}
    if(code.includes('getBoundingClientRect')) return [];
    return scrollTop;
  },
  waitForTimeout: async ()=>{},
  context: ()=>({newPage: async ()=>({
    evaluate: async ()=>Buffer.from('synthetic composite').toString('base64'),
    close: async ()=>{},
  })}),
};
captureScrollSurface(page,{
  filePath:path.join(directory,'dashboard.png'), timeout:1000,
  pngEvidence:()=>({width:584*scale,height:916*scale}), measure:async()=>({}),
}).then(result=>{
  const positions=result.tiles.map(tile=>tile.scrollTop);
  if(JSON.stringify(positions)!==JSON.stringify([0,620,620+remainder]))
    throw new Error(`Missing final scroll position: ${positions}`);
  if(result.composition.canvasHeight!==(1536+remainder)*scale)
    throw new Error('Incorrect composite height');
  console.log(JSON.stringify({positions,height:result.composition.canvasHeight}));
}).catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(COMPOSITOR),
            str(tmp_path),
            str(remainder),
            str(scale),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {
        "positions": [0, 620, 620 + remainder],
        "height": (1536 + remainder) * scale,
    }
