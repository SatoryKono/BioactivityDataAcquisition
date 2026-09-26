"""Compact replay verdict with a separate, readable evidence table."""

from copy import deepcopy


def compact_replay_first_window(payload: dict) -> None:
    """Share the scope band with readiness and fit the five retention rows."""
    panels = {p["id"]: p for p in payload["panels"]}
    if not {9400, 9422, 9418, 9416} <= panels.keys():
        return
    old_bottom = max(
        panels[pid]["gridPos"]["y"] + panels[pid]["gridPos"]["h"]
        for pid in (9418, 9416)
    )
    panels[9400]["gridPos"].update(x=0, y=2, w=16, h=3)
    panels[9422]["gridPos"].update(x=16, y=2, w=8, h=3)
    for pid, x, width in ((9418, 0, 15), (9416, 15, 9)):
        panels[pid]["gridPos"].update(x=x, y=5, w=width, h=7)
    shift = 12 - old_bottom

    def move(panel: dict) -> None:
        panel["gridPos"]["y"] += shift
        for child in panel.get("panels", []):
            move(child)

    for panel in panels.values():
        if panel["gridPos"]["y"] >= old_bottom:
            move(panel)


def apply_replay_readiness_design(payload: dict) -> None:
    if payload.get("uid") != "bioetl-control-plane-v1":
        return
    panels = payload["panels"]
    card = next((p for p in panels if p.get("id") == 9422), None)
    row = next((p for p in panels if p.get("id") == 902), None)
    if card is None or row is None:
        return
    card.update(type="stat", title="Review Exact Replay Readiness")
    card["options"] = {
        "reduceOptions": {
            "values": False,
            "calcs": ["lastNotNull"],
            "fields": "verdict",
        },
        "orientation": "horizontal",
        "textMode": "value",
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "text": {"valueSize": 22},
    }
    card["transformations"] = [
        {"id": "filterFieldsByName", "options": {"include": {"names": ["verdict"]}}}
    ]
    colors = {
        "READY": "green",
        "BLOCKED": "red",
        "INSUFFICIENT": "orange",
        "UNSUPPORTED": "#555555",
        "SELECT RUN": "#555555",
        "QUERY ERROR": "red",
    }
    card["fieldConfig"] = {
        "defaults": {
            "unit": "none",
            "noValue": (
                "SELECT RUN if no Run ID is selected. "
                "QUERY ERROR if the request failed."
            ),
            "mappings": [
                {
                    "type": "value",
                    "options": {
                        state: {"text": state, "color": color}
                        for state, color in colors.items()
                    },
                }
            ],
            "color": {"mode": "thresholds"},
            "thresholds": {
                "mode": "absolute",
                "steps": [{"color": "#555555", "value": None}],
            },
        },
        "overrides": [],
    }
    card["links"] = [
        {
            "title": "View replay checks",
            "url": "/d/bioetl-control-plane-v1/1-trust?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&viewPanel=9423&${__url_time_range}",
            "targetBlank": False,
        }
    ]
    children = row.setdefault("panels", [])
    children[:] = [p for p in children if p.get("id") != 9423]
    target = deepcopy(card["targets"][0])
    target["root_selector"] = "replay_checks"
    bottom = max(
        (p["gridPos"]["y"] + p["gridPos"]["h"] for p in children),
        default=row["gridPos"]["y"] + 1,
    )
    children.append(
        {
            "id": 9423,
            "type": "table",
            "title": "Review Exact Replay Checks",
            "description": (
                "SELECTED RUN · One row per readiness check for this Run ID. "
                "Fail blocks replay. Unknown is not a pass."
            ),
            "datasource": card["datasource"],
            "targets": [target],
            "gridPos": {"x": 0, "y": bottom, "w": 24, "h": 8},
            "options": {
                "showHeader": True,
                "cellHeight": "lg",
                "footer": {"show": False, "enablePagination": True},
            },
            "transformations": [
                {
                    "id": "organize",
                    "options": {
                        "indexByName": {
                            "code": 0,
                            "result": 1,
                            "reason": 2,
                            "evidence_ref": 3,
                        },
                        "renameByName": {
                            "code": "Check",
                            "result": "Result",
                            "reason": "Reason",
                            "evidence_ref": "Evidence reference",
                        },
                    },
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "noValue": "—",
                    "custom": {
                        "align": "left",
                        "inspect": True,
                        "wrapText": True,
                        "cellOptions": {"type": "auto", "wrapText": True},
                    },
                },
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Check"},
                        "properties": [
                            {
                                "id": "mappings",
                                "value": [
                                    {
                                        "type": "value",
                                        "options": {
                                            "manifest_not_recorded": {
                                                "text": "manifest этого запуска не найден"
                                            }
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        }
    )
