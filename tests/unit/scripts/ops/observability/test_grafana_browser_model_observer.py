"""Grafana 12 browser DTO evidence must preserve semantics and exact identity."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts.ops.observability.grafana import rerender_grafana_screenshots as rerender
from scripts.ops.observability.grafana.capture_provenance import model_errors

pytestmark = pytest.mark.unit


def test_actual_dto_envelope_preserves_spec_and_binds_resource_name():
    node = rerender._resolve_node_executable()
    if node is None:
        pytest.skip("Node.js is unavailable")
    env = os.environ.copy()
    rerender._apply_playwright_runtime_env(env)
    program = r"""
const fs = require('fs');
const {browserDashboardResponseKind: kind, normalizeBrowserDashboardPayload: normalize} = require(process.argv[1]);
const source = JSON.parse(fs.readFileSync('grafana/dashboards/bioetl-overview-v2.json','utf8'));
const uid = source.uid;
const spec = {...source, schemaVersion:42};
delete spec.uid;
const dto = {kind:'DashboardWithAccessInfo',apiVersion:'dashboard.grafana.app/v1beta1',
  metadata:{name:uid,uid:'resource-uid-is-not-dashboard-uid',namespace:'default'},spec};
const base = 'http://localhost:3003';
const dtoUrl = `${base}/apis/dashboard.grafana.app/v1beta1/namespaces/default/dashboards/${uid}/dto`;
const legacyUrl = `${base}/api/dashboards/uid/${uid}`;
const loaded = normalize(dto,kind(dtoUrl,base,uid),uid);
const preserved = JSON.stringify(loaded) === JSON.stringify({...spec,uid});
const routes = {
  dto:kind(dtoUrl+'?x=1',base,uid),legacy:kind(legacyUrl,base,uid),
  foreignOrigin:kind(dtoUrl.replace(base,'http://foreign.example'),base,uid),
  foreignUid:kind(dtoUrl.replace(uid,'foreign'),base,uid),
  unrelated:kind(`${base}/api/annotations?dashboardUID=${uid}`,base,uid),
};
const rejected = [];
for (const [label,value] of [
  ['foreign-name',{...dto,metadata:{...dto.metadata,name:'foreign'}}],
  ['foreign-spec-uid',{...dto,spec:{...spec,uid:'foreign'}}],
  ['foreign-api',{...dto,apiVersion:'unknown/v1'}],
  ['foreign-kind',{...dto,kind:'Unknown'}],
  ['array-spec',{...dto,spec:[]}],
  ['absent-spec',{...dto,spec:null}],
]) {
  try {normalize(value,'grafana-v1beta1-dto',uid);} catch {rejected.push(label);}
}
let foreignLegacyRejected=false;
try {normalize({dashboard:{...source,uid:'foreign'}},'legacy',uid);} catch {foreignLegacyRejected=true;}
console.log(JSON.stringify({preserved,loadedUid:loaded.uid,schemaVersion:loaded.schemaVersion,routes,rejected,
  foreignLegacyRejected,legacyPreserved:normalize({dashboard:source},'legacy',uid)===source}));
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
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["preserved"] is True
    assert observed["loadedUid"] == "bioetl-overview-v2"
    assert observed["schemaVersion"] == 42
    assert observed["routes"] == {
        "dto": "grafana-v1beta1-dto",
        "legacy": "legacy",
        "foreignOrigin": None,
        "foreignUid": None,
        "unrelated": None,
    }
    assert observed["rejected"] == [
        "foreign-name",
        "foreign-spec-uid",
        "foreign-api",
        "foreign-kind",
        "array-spec",
        "absent-spec",
    ]
    assert observed["foreignLegacyRejected"] is True
    assert observed["legacyPreserved"] is True


def test_browser_migration_remains_a_source_parity_failure():
    source = {"uid": "example", "schemaVersion": 30, "panels": []}
    migrated = {**source, "schemaVersion": 42}
    assert model_errors(
        source, {"before": source, "loaded": [migrated], "after": source}
    ) == ["loaded provisioned model differs from source"]
    assert model_errors(source, {"before": source, "loaded": [], "after": source}) == [
        "missing browser-loaded model"
    ]
