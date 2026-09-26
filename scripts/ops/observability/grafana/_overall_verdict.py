"""Compact selected-run verdict using the overview's existing source frame."""

from copy import deepcopy


def apply_overall_verdict(payload: dict) -> None:
    """Keep the headline and status table bound to the same saved assessment."""
    if payload.get("uid") != "bioetl-overview-v2":
        return
    panels = payload["panels"]
    source = next(p for p in panels if p["id"] == 9603)
    next(p for p in panels if p["id"] == 99)["gridPos"].update(w=17)
    panel = {
        "id": 9604,
        "type": "stat",
        "title": "Overall verdict",
        "description": "Saved overall verdict for the selected Run ID, identical to Review Selected Run Status. This verdict does not authorize replay. Missing evidence remains UNKNOWN; request errors remain errors.",
        "gridPos": {"x": 17, "y": 2, "w": 7, "h": 3},
        "datasource": deepcopy(source["datasource"]),
        "targets": deepcopy(source["targets"]),
        "transformations": [
            {"id": "limit", "options": {"limitField": 1}},
            {
                "id": "filterFieldsByName",
                "options": {"include": {"names": ["run_verdict"]}},
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "none",
                "noValue": "UNKNOWN",
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            value: {"text": value, "color": color}
                            for value, color in {
                                "OK": "green",
                                "WARN": "yellow",
                                "ERROR": "red",
                                "INCOMPLETE": "orange",
                                "UNKNOWN": "gray",
                                "N/A": "gray",
                                "QUERY ERROR": "red",
                                "SELECT RUN": "gray",
                            }.items()
                        },
                    }
                ],
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"],
                "fields": "/.*/",
            },
            "orientation": "auto",
            "textMode": "value",
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "center",
        },
    }
    panels[:] = [p for p in panels if p["id"] != panel["id"]]
    panels.insert(2, panel)
