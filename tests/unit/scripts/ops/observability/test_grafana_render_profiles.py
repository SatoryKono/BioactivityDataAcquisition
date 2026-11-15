"""Profile-specific render sources must match the dashboard being inspected."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.ops.observability.grafana import rerender_grafana_screenshots as subject

pytestmark = pytest.mark.unit


def test_adaptive_profile_selects_its_model_and_source_digest(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "_repo_root", lambda: tmp_path)
    for directory, title in (
        ("dashboards", "Native row"),
        ("dashboards-adaptive", "Current row"),
    ):
        folder = tmp_path / "grafana" / directory
        folder.mkdir(parents=True)
        (folder / "dashboard.json").write_text(
            json.dumps({"uid": "same-uid", "title": title, "version": 2}),
            encoding="utf-8",
        )
    config = subject.RenderConfig(
        base_url="http://localhost",
        username="",
        password="",
        service_account_token="",
        output_dir=tmp_path / "screens",
        width=1366,
        height=768,
        timeout_seconds=10,
        selected_uids=(),
        fallback="playwright",
        dashboard_profile="adaptive",
    )
    assert subject._load_dashboards(config)[0].title == "Current row"
    assert (
        subject._load_dashboards(replace(config, dashboard_profile="native"))[0].title
        == "Native row"
    )
    source = subject._dashboard_source_by_uid(config.dashboard_profile)["same-uid"]
    expected = tmp_path / "grafana/dashboards-adaptive/dashboard.json"
    assert source["path"] == "grafana/dashboards-adaptive/dashboard.json"
    assert source["sha256"] == hashlib.sha256(expected.read_bytes()).hexdigest()


def test_unknown_profile_cannot_select_an_arbitrary_source_path():
    with pytest.raises(ValueError, match="Unknown dashboard profile"):
        subject._dashboard_dir("../../foreign")


def test_browser_selects_adaptive_sources_and_enforces_plugin_containment():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for browser helper contracts")
    script = Path(subject.__file__).with_suffix(".cjs")
    code = """
const render = require(process.argv[1]);
let blocked = false;
try { render.dashboardDir('../../foreign'); } catch { blocked = true; }
const panels = render.selectContainmentPanels([{id: 9406, type: 'bioetl-selectorshell-panel', gridPos: {x: 0, y: 5, w: 24, h: 5}}], false);
process.stdout.write(JSON.stringify({path: render.dashboardDir('adaptive'), blocked, ids: panels.map(panel => panel.id)}));
"""
    result = subprocess.run(
        [node, "-e", code, str(script)],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    payload = json.loads(result.stdout)
    assert Path(payload["path"]).name == "dashboards-adaptive"
    assert payload["blocked"] is True
    assert payload["ids"] == [9406]


def test_browser_kiosk_closes_menu_only_when_requested():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for browser helper contracts")
    script = Path(subject.__file__).with_suffix(".cjs")
    code = """
const {applyRequestedKioskUi} = require(process.argv[1]);
(async () => {
  let clicks = 0;
  const page = {getByRole:(role,options) => {
    if (role !== 'button' || options.name !== 'Close menu' || !options.exact) throw new Error('unexpected control');
    return {count:async()=>1,isVisible:async()=>true,click:async()=>{clicks++},waitFor:async()=>{}};
  },waitForTimeout:async()=>{}};
  await applyRequestedKioskUi(page,'off');
  const offClicks = clicks;
  await applyRequestedKioskUi(page,'tv');
  process.stdout.write(JSON.stringify({offClicks,tvClicks:clicks}));
})().catch(error=>{console.error(error);process.exitCode=1});
"""
    result = subprocess.run(
        [node, "-e", code, str(script)],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    assert json.loads(result.stdout) == {"offClicks": 0, "tvClicks": 1}


def test_kiosk_gate_distinguishes_menu_toggle_from_an_open_sidebar():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for browser helper contracts")
    script = Path(subject.__file__).with_suffix(".cjs")
    code = """
const {browserAndKioskStateFromDom} = require(process.argv[1]);
const element = tagName => ({tagName,getAttribute:()=>null,getBoundingClientRect:()=>({width:32,height:32})});
const toggle = element('BUTTON');
const sidebar = element('NAV');
let open = false;
global.window = {location:{href:'http://localhost/d/test?kiosk=tv'},innerWidth:1366,innerHeight:768,devicePixelRatio:1,visualViewport:{scale:1}};
global.getComputedStyle = () => ({display:'block',visibility:'visible',opacity:'1',zoom:'1'});
global.document = {documentElement:{},querySelectorAll:selector => selector.includes('Main menu') ? [toggle] : selector.includes('navigation mega-menu') && open ? [sidebar] : []};
const args = {requestedZoom:100,requestedKiosk:'tv',physicalViewport:{width:1366,height:768}};
const collapsed = browserAndKioskStateFromDom(args);
open = true;
const expanded = browserAndKioskStateFromDom(args);
process.stdout.write(JSON.stringify({collapsed:collapsed.actualKiosk,expanded:expanded.actualKiosk}));
"""
    result = subprocess.run(
        [node, "-e", code, str(script)],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    assert json.loads(result.stdout) == {"collapsed": "tv", "expanded": "off"}
