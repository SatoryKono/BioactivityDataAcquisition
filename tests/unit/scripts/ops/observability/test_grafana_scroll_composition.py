"""Verify that exported scroll captures preserve every document row."""

import json
from pathlib import Path
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[5]
COMPOSITOR = REPO_ROOT / "scripts/ops/observability/grafana/capture_scroll_surface.cjs"


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
"""
    subprocess.run(
        ["node", "-e", script, str(COMPOSITOR), str(scale), json.dumps(offsets)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_incomplete_capture_is_rejected():
    script = r"""
const {compositionSlices} = require(process.argv[1]);
try {
  compositionSlices({top:232,stickyBottom:232,clientHeight:684,scrollHeight:902,scale:1},
    [{scrollTop:0,height:916}]);
} catch(error) {
  if (error.message.includes('incomplete document')) process.exit(0);
  throw error;
}
throw new Error('Incomplete capture was accepted');
"""
    subprocess.run(
        ["node", "-e", script, str(COMPOSITOR)],
        check=True,
        capture_output=True,
        text=True,
    )


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
"""
    subprocess.run(
        ["node", "-e", script, str(COMPOSITOR), str(scale)],
        check=True,
        capture_output=True,
        text=True,
    )


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
}).catch(error=>{console.error(error);process.exitCode=1;});
"""
    subprocess.run(
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
