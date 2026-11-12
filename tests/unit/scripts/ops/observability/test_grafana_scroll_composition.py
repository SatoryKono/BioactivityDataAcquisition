"""Scrolling PNGs retain every document row and exclude sticky-header paint."""

import json
import subprocess

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("scale", [1, 2])
@pytest.mark.parametrize("offsets", [[0, 218], [0, 620, 1240, 1418]])
def test_composition_keeps_original_rows_without_overwriting_them_with_chrome(
    scale, offsets
):
    program = r"""
const {compositionSlices}=require('./scripts/ops/observability/grafana/capture_scroll_surface.cjs');
const [scale, offsets]=JSON.parse(process.argv[1]);
const surface={top:232,stickyBottom:232,clientHeight:684,scrollHeight:684+offsets.at(-1),scale};
const tiles=offsets.map(scrollTop=>({scrollTop,height:916*scale}));
const {canvasHeight,slices}=compositionSlices(surface,tiles);
const actual=[];
for(let i=0;i<tiles.length;i++){
  // The top of every later viewport contains the sticky toolbar plus shadow.
  const pixels=Array.from({length:tiles[i].height},(_,y)=>i>0 && y<264*scale ? -1 : y+offsets[i]*scale);
  const s=slices[i];actual.push(...pixels.slice(s.sourceY,s.sourceY+s.height));
}
process.stdout.write(JSON.stringify({correct:actual.every((value,y)=>value===y),length:actual.length,canvasHeight}));
"""
    result = json.loads(
        subprocess.check_output(
            ["node", "-e", program, json.dumps([scale, offsets])], text=True
        )
    )
    assert result["correct"]
    assert result["length"] == result["canvasHeight"] == (916 + offsets[-1]) * scale


def test_incomplete_tiles_are_rejected_instead_of_exporting_a_truncated_image():
    program = """
const {compositionSlices}=require('./scripts/ops/observability/grafana/capture_scroll_surface.cjs');
try { compositionSlices({top:232,stickyBottom:232,clientHeight:684,scrollHeight:902,scale:1},[{scrollTop:0,height:916}]); }
catch(error){process.stdout.write(error.message);process.exit(0);}
process.exit(1);
"""
    result = subprocess.check_output(["node", "-e", program], text=True)
    assert "incomplete document" in result
