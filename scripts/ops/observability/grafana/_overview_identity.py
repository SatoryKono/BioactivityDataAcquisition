"""Compact, persisted identity for the Overview first window."""

from copy import deepcopy


def apply_overview_identity(payload: dict) -> None:
    """Keep the exact run key visible; retain manifest details below the fold."""
    panels = payload["panels"]
    identity = next(p for p in panels if p.get("id") == 9300)
    if not any(p.get("id") == 9399 for p in panels):
        details = deepcopy(identity)
        details.update(id=9390, title="Inspect Full Run Identity")
        details["gridPos"] = {"x": 0, "y": 19, "w": 24, "h": 12}
        panels.append(
            {
                "id": 9399,
                "type": "row",
                "title": "Inspect Additional Run Identity",
                "collapsed": True,
                "gridPos": {"x": 0, "y": 18, "w": 24, "h": 1},
                "panels": [details],
            }
        )
    detail_row = next(p for p in panels if p.get("id") == 9399)
    detail_row["gridPos"].update(y=18)
    for detail in detail_row["panels"]:
        detail["gridPos"].update(y=19)
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
        "Manifest, schema and available source revision are in Inspect Additional Run Identity. "
        "Missing saved values are Not recorded; request failures remain query errors."
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
