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
const surface = {top:232, stickyBottom:232, scrollHeight:684+offsets.at(-1), scale};
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
  compositionSlices({top:232,stickyBottom:232,scrollHeight:902,scale:1},
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
