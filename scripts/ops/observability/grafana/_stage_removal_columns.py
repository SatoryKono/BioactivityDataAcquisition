"""Attach exact-run saved layer counters to Data Quality stage diagnostics."""

from copy import deepcopy


def apply_stage_removal_columns(payload: dict) -> None:
    """Join saved report counters without substituting current telemetry."""
    if payload.get("uid") != "bioetl-dq-v2":
        return
    pending = list(payload["panels"])
    while pending:
        panel = pending.pop()
        pending.extend(panel.get("panels", []))
        if panel.get("id") != 9460:
            continue
        fields = ["quarantined", "excluded", "deduplicated", "filtered_out"]
        projection = (
            "($l := layers; $v := function($k){$x := $lookup($l,$k); "
            "$type($x) = 'number' and $x >= 0 ? $x : null}; "
            "$map(funnel, function($s){ {'stage_id':$s.stage_id, "
            "'quarantined':$v($s.stage_id & '_quarantined'), "
            "'excluded':$v($s.stage_id & '_excluded_by_contract'), "
            "'deduplicated':$v($s.stage_id & '_deduplicated'), "
            "'filtered_out':$v($s.stage_id & '_filtered_out')} }))"
        )
        target = deepcopy(panel["targets"][0])
        target.update(
            refId="B",
            parser="uql",
            root_selector=projection,
            uql='parse-json | jsonata "' + projection + '"',
            url=(
                "/ops/observability/pipeline-run-report-artifact"
                "?pipeline=${pipeline:percentencode}&run_id=${run_id:percentencode}"
                "&format=pipeline_run_report_json"
            ),
        )
        panel["targets"] = [panel["targets"][0], target]
        panel["transformations"] = [
            t for t in panel["transformations"] if t["id"] != "joinByField"
        ]
        panel["transformations"].insert(
            0,
            {
                "id": "joinByField",
                "options": {"byField": "stage_id", "mode": "outerTabular"},
            },
        )
        order = [
            "stage_id",
            "state",
            "reason",
            "records_in",
            "records_out",
            *fields,
            "duration_seconds",
            "source",
        ]
        for transform in panel["transformations"]:
            if transform["id"] == "filterFieldsByName":
                transform["options"]["include"]["names"] = order
            elif transform["id"] == "organize":
                transform["options"]["indexByName"] = {
                    name: i for i, name in enumerate(order)
                }
                transform["options"].setdefault("renameByName", {}).update(
                    quarantined="Quarantined",
                    excluded="Excluded",
                    deduplicated="Deduplicated",
                    filtered_out="Filtered out",
                )
        note = " Removal counters come from saved report layers; absent counters remain UNKNOWN."
        if note not in panel["description"]:
            panel["description"] += note
