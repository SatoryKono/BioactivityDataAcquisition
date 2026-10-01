"""Compact, persisted identity for the Overview first window."""


def apply_overview_identity(payload: dict) -> None:
    """Keep only the compact exact-run identity on Overview."""
    panels = payload["panels"]
    panels[:] = [panel for panel in panels if panel.get("id") not in {9301, 9399, 9390}]
    by_id = {panel["id"]: panel for panel in panels}
    by_id[9002]["gridPos"].update(x=0, y=5, w=15, h=12)
    by_id[9603]["gridPos"].update(x=15, y=5, w=9, h=4)
    identity = next(p for p in panels if p.get("id") == 9300)
    identity["gridPos"].update(x=15, y=9, w=9, h=8)
    target = identity["targets"][0]
    target.update(
        url="/ops/observability/selected-run-status?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}&workflow=${workflow:csv}",
        root_selector=(
            '($v := function($x){$exists($x) and $x != "" ? $string($x) : '
            '"Not recorded in saved run evidence"}; ['
            '{"parameter":"Run ID","value":$v(run_id)},'
            '{"parameter":"Pipeline","value":$v(pipeline)},'
            '{"parameter":"Run Type","value":$v(run_type)},'
            '{"parameter":"Started at","value":'
            'started_at ? $substring(started_at,0,10) & " " & '
            '$substring(started_at,11,5) & " " & '
            '($substring(started_at,-1) = "Z" ? "UTC" : $substring(started_at,-6)) : '
            '"Not recorded in saved run evidence"}])'
        ),
    )
    identity["description"] = (
        "SELECTED RUN · Pipeline and full Run ID identify the saved run. "
        "Run Type and Started at (with saved UTC offset) characterize its execution. "
        "SELECT RUN means no selected run context. Missing saved values are Not recorded; request failures remain QUERY ERROR."
    )
    identity["options"] = {
        "showHeader": True,
        "cellHeight": "sm",
        "footer": {"show": False, "enablePagination": False},
    }
    identity["fieldConfig"] = {
        "defaults": {
            "custom": {
                "align": "left",
                "inspect": True,
                "wrapText": True,
                "cellOptions": {"type": "auto", "wrapText": True},
            }
        },
        "overrides": [
            {
                "matcher": {"id": "byName", "options": "Parameter"},
                "properties": [{"id": "custom.width", "value": 125}],
            }
        ],
    }
    identity["transformations"] = [
        {
            "id": "organize",
            "options": {
                "indexByName": {"parameter": 0, "value": 1},
                "renameByName": {"parameter": "Parameter", "value": "Value"},
            },
        }
    ]
