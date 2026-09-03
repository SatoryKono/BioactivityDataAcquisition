import json, pathlib, yaml
# Fix runtime
rt_path = pathlib.Path("grafana/dashboards/bioetl-runtime.json")
rt = json.loads(rt_path.read_text(encoding="utf-8"))
panel = next(p for p in rt["panels"] if p.get("id")==9101)
panel["fieldConfig"]["defaults"]["links"] = [
    {"title": "Open Runtime", "url": "/d/bioetl-runtime/bioetl-runtime?var-workflow=$workflow&var-pipeline=$pipeline&var-run_type=$run_type&var-stage=$__all&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
    {"title": "Open Trust", "url": "/d/bioetl-control-plane-v1/bioetl-control-plane-v1?var-workflow=$workflow&var-pipeline=$pipeline&var-run_type=$run_type&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
    {"title": "Open Data Quality", "url": "/d/bioetl-dq-v2/bioetl-dq-v2?var-workflow=$workflow&var-pipeline=$pipeline&var-run_type=$run_type&var-stage=$__all&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
    {"title": "Open Run Explorer", "url": "/d/bioetl-run-explorer-v1/bioetl-run-explorer-v1?var-workflow=$workflow&var-pipeline=$pipeline&var-run_type=$run_type&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
]
for ov in panel["fieldConfig"]["overrides"]:
    if ov.get("matcher",{}).get("options")=="action_target":
        for prop in ov["properties"]:
            if prop["id"]=="links":
                prop["value"] = [
                    {"title": "Open Runtime", "url": "/d/bioetl-runtime/bioetl-runtime?var-workflow=${__data.fields.workflow}&var-pipeline=${__data.fields.pipeline}&var-run_type=${__data.fields.run_type}&var-stage=$__all&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
                    {"title": "Open Trust", "url": "/d/bioetl-control-plane-v1/bioetl-control-plane-v1?var-workflow=${__data.fields.workflow}&var-pipeline=${__data.fields.pipeline}&var-run_type=${__data.fields.run_type}&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
                    {"title": "Open Data Quality", "url": "/d/bioetl-dq-v2/bioetl-dq-v2?var-workflow=${__data.fields.workflow}&var-pipeline=${__data.fields.pipeline}&var-run_type=${__data.fields.run_type}&var-stage=$__all&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
                    {"title": "Open Run Explorer", "url": "/d/bioetl-run-explorer-v1/bioetl-run-explorer-v1?var-workflow=${__data.fields.workflow}&var-pipeline=${__data.fields.pipeline}&var-run_type=${__data.fields.run_type}&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
                ]
            if prop["id"]=="custom.width":
                prop["value"]=70
            if prop["id"]=="mappings":
                prop["value"]=[
                    {"type": "value", "options": {"runtime": {"text": "Runtime", "color": "red"}, "control_plane": {"text": "Control Plane", "color": "red"}, "data_quality": {"text": "Data Quality", "color": "orange"}, "workflow": {"text": "Workflow", "color": "orange"}}},
                    {"type": "special", "options": {"match": "null", "result": {"text": "UNKNOWN", "color": "gray"}}},
                    {"type": "special", "options": {"match": "nan", "result": {"text": "UNKNOWN", "color": "gray"}}},
                ]
rt_path.write_text(json.dumps(rt, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("runtime fixed")

# Fix DQ
dq_path = pathlib.Path("grafana/dashboards/bioetl-dq-v2.json")
dq = json.loads(dq_path.read_text(encoding="utf-8"))
panel2 = next(p for p in dq["panels"] if p.get("id")==9102)
panel2["fieldConfig"]["defaults"]["links"] = [
    {"title": "Open Data Quality evidence", "url": "/d/bioetl-dq-v2/bioetl-dq-v2?var-workflow=$workflow&var-pipeline=$pipeline&var-run_type=$run_type&var-stage=$__all&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
]
for ov in panel2["fieldConfig"]["overrides"]:
    if ov.get("matcher",{}).get("options")=="action_target":
        for prop in ov["properties"]:
            if prop["id"]=="links":
                prop["value"] = [
                    {"title": "Open Data Quality evidence", "url": "/d/bioetl-dq-v2/bioetl-dq-v2?var-workflow=$workflow&var-pipeline=${__data.fields.pipeline}&var-run_type=$run_type&var-stage=$__all&var-run_id=$run_id&${__url_time_range}", "targetBlank": False, "includeVars": False},
                    {"title": "Open DQ reason-rules runbook", "url": "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/observability-checklist.md", "targetBlank": True, "includeVars": False},
                ]
            if prop["id"]=="mappings":
                prop["value"]=[
                    {"type": "value", "options": {"data_quality": {"text": "Data Quality", "color": "orange"}, "verify_dq_reason_rules": {"text": "Verify DQ rules", "color": "gray"}}},
                    {"type": "special", "options": {"match": "null", "result": {"text": "UNKNOWN", "color": "gray"}}},
                    {"type": "special", "options": {"match": "nan", "result": {"text": "UNKNOWN", "color": "gray"}}},
                ]
            if prop["id"]=="custom.width":
                prop["value"]=90
dq_path.write_text(json.dumps(dq, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("dq fixed")

# Fix yaml
yp = pathlib.Path("docs/03-guides/dashboards/contracts/navigation-links.yaml")
import yaml
data = yaml.safe_load(yp.read_text(encoding="utf-8"))
rpl = data.get("required_panel_links_by_uid", {})
# runtime
rt_entries = list(rpl.get("bioetl-runtime", []))
existing = {(e.get("panel_id"), e.get("target_uid")) for e in rt_entries}
for e in [{"panel_id": 9101, "target_uid": "bioetl-runtime", "link_titles": ["Open Runtime"]}, {"panel_id": 9101, "target_uid": "bioetl-control-plane-v1", "link_titles": ["Open Trust"]}, {"panel_id": 9101, "target_uid": "bioetl-dq-v2", "link_titles": ["Open Data Quality"]}]:
    if (e["panel_id"], e["target_uid"]) not in existing:
        rt_entries.append(e)
rpl["bioetl-runtime"] = rt_entries
# dq
dq_entries = list(rpl.get("bioetl-dq-v2", []))
existing_dq = {(e.get("panel_id"), e.get("target_uid")) for e in dq_entries}
add = {"panel_id": 9102, "target_uid": "bioetl-dq-v2", "link_titles": ["Open Data Quality evidence"]}
if (add["panel_id"], add["target_uid"]) not in existing_dq:
    dq_entries.append(add)
rpl["bioetl-dq-v2"] = dq_entries
data["required_panel_links_by_uid"] = rpl
yp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
print("yaml fixed")
