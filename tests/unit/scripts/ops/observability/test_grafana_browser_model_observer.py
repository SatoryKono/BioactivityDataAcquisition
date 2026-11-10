"""Grafana 12 browser DTO evidence must preserve semantics and exact identity."""

from __future__ import annotations

import json
import copy
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
const v2 = {...dto,apiVersion:'dashboard.grafana.app/v2',spec:{elements:{},layout:{}}};
const v2Preserved = normalize(v2,'grafana-v2-dto',uid) === v2;
let v2ArrayRejected = false;
try {normalize({...v2,spec:{elements:[],layout:{}}},'grafana-v2-dto',uid);} catch {v2ArrayRejected=true;}
const preserved = JSON.stringify(loaded) === JSON.stringify({...spec,uid});
const routes = {
  dto:kind(dtoUrl+'?x=1',base,uid),legacy:kind(legacyUrl,base,uid),
  v2:kind(dtoUrl.replace('v1beta1','v2'),base,uid),
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
console.log(JSON.stringify({preserved,v2Preserved,v2ArrayRejected,loadedUid:loaded.uid,schemaVersion:loaded.schemaVersion,routes,rejected,
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
    assert observed["v2Preserved"] is True
    assert observed["v2ArrayRejected"] is True
    assert observed["loadedUid"] == "bioetl-overview-v2"
    assert observed["schemaVersion"] == 42
    assert observed["routes"] == {
        "dto": "grafana-v1beta1-dto",
        "v2": "grafana-v2-dto",
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


def _v2_evidence():
    panel = {
        "id": 1,
        "type": "stat",
        "title": "Count",
        "gridPos": {"x": 0, "y": 0, "w": 24, "h": 5},
        "targets": [
            {
                "refId": "A",
                "expr": "up",
                "datasource": {"type": "prometheus", "uid": "prom"},
            }
        ],
    }
    source = {"uid": "example", "version": 7, "panels": [panel]}
    dto = {
        "kind": "DashboardWithAccessInfo",
        "apiVersion": "dashboard.grafana.app/v2",
        "metadata": {"name": "example", "generation": 7, "resourceVersion": "123"},
        "spec": {
            "elements": {
                "panel-1": {
                    "kind": "Panel",
                    "spec": {
                        "id": 1,
                        "title": "Count",
                        "vizConfig": {
                            "group": "stat",
                            "spec": {
                                "options": {},
                                "fieldConfig": {"defaults": {}, "overrides": []},
                            },
                        },
                        "data": {
                            "kind": "QueryGroup",
                            "spec": {
                                "queryOptions": {},
                                "transformations": [],
                                "queries": [
                                    {
                                        "kind": "PanelQuery",
                                        "spec": {
                                            "refId": "A",
                                            "hidden": False,
                                            "query": {
                                                "kind": "DataQuery",
                                                "group": "prometheus",
                                                "version": "v0",
                                                "datasource": {"name": "prom"},
                                                "spec": {"expr": "up"},
                                            },
                                        },
                                    }
                                ],
                            },
                        },
                    },
                }
            },
            "layout": {
                "kind": "GridLayout",
                "spec": {
                    "items": [
                        {
                            "kind": "GridLayoutItem",
                            "spec": {
                                "element": {
                                    "kind": "ElementReference",
                                    "name": "panel-1",
                                },
                                "x": 0,
                                "y": 0,
                                "width": 24,
                                "height": 5,
                            },
                        }
                    ]
                },
            },
        },
    }
    return source, {
        "before": source,
        "loaded": [],
        "after": source,
        "v2": {
            "before": copy.deepcopy(dto),
            "loaded": [copy.deepcopy(dto)],
            "after": copy.deepcopy(dto),
        },
    }


def test_v2_browser_model_matches_same_provisioned_generation():
    source, evidence = _v2_evidence()
    assert model_errors(source, evidence) == []


@pytest.mark.parametrize("mutation", ["lost_panels", "query", "layout", "field_config"])
def test_consistently_wrong_v2_conversion_is_rejected(mutation):
    source, evidence = _v2_evidence()
    for dto in (
        evidence["v2"]["before"],
        *evidence["v2"]["loaded"],
        evidence["v2"]["after"],
    ):
        spec = dto["spec"]
        if mutation == "lost_panels":
            spec["elements"] = {}
            spec["layout"] = {}
        elif mutation == "query":
            spec["elements"]["panel-1"]["spec"]["data"]["spec"]["queries"][0]["spec"][
                "query"
            ]["spec"]["expr"] = "vector(0)"
        elif mutation == "layout":
            spec["layout"]["spec"]["items"][0]["spec"]["width"] = 1
        else:
            spec["elements"]["panel-1"]["spec"]["vizConfig"]["spec"]["fieldConfig"][
                "defaults"
            ]["unit"] = "percent"
    assert model_errors(source, evidence)


@pytest.mark.parametrize("phase", ["before", "loaded", "after"])
@pytest.mark.parametrize(
    "mutation", ["missing", "query", "uid", "generation", "resource", "schema"]
)
def test_v2_substitution_or_missing_evidence_fails(phase, mutation):
    source, evidence = _v2_evidence()
    model = evidence["v2"][phase][0] if phase == "loaded" else evidence["v2"][phase]
    if mutation == "missing":
        evidence["v2"][phase] = [] if phase == "loaded" else None
    elif mutation == "query":
        model["spec"]["elements"] = {"panel": {"expr": "vector(0)"}}
    elif mutation == "uid":
        model["metadata"]["name"] = "foreign"
    elif mutation == "generation":
        model["metadata"]["generation"] = 8
    elif mutation == "resource":
        del model["metadata"]["resourceVersion"]
    else:
        model["metadata"] = ["invalid"]
    assert model_errors(source, evidence)
