"""Attach exact-run saved per-stage removal counters to stage diagnostics."""

from copy import deepcopy


def apply_stage_removal_columns(payload: dict) -> None:
    """Join saved report counters without substituting current telemetry."""
    if payload.get("uid") not in {
        "bioetl-runtime",
        "bioetl-dq-v2",
        "bioetl-overview-v2",
        "bioetl-incident-v1",
    }:
        return
    pending = list(payload["panels"])
    while pending:
        panel = pending.pop()
        pending.extend(panel.get("panels", []))
        if panel.get("id") != 9460:
            continue
        fields = ["quarantined", "excluded", "deduplicated", "filtered_out"]
        projection = (
            "($r := function($s,$o){$exists($s.removals[outcome=$o]) "
            "? $sum($s.removals[outcome=$o].count) "
            ": ($s.tracking = 'full' ? 0 : null)}; "
            "$map(funnel, function($s){ {'stage_id':$s.stage_id, "
            "'quarantined':$r($s,'quarantined'), "
            "'excluded':$r($s,'excluded_by_contract'), "
            "'deduplicated':$r($s,'deduplicated'), "
            "'filtered_out':$r($s,'filtered_out')} }))"
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
        if payload.get("uid") == "bioetl-overview-v2":
            order.remove("duration_seconds")
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
        old_notes = (
            " Removal counters come from saved report layers;"
            " absent counters remain UNKNOWN.",
        )
        note = (
            " Removal counters are per-stage saved funnel removals;"
            " untracked stages stay UNKNOWN."
        )
        description = str(panel.get("description") or "")
        for old in old_notes:
            description = description.replace(old, "")
        panel["description"] = (
            description.rstrip() if note in description else description.rstrip() + note
        )
        panel["fieldConfig"]["defaults"]["noValue"] = "UNKNOWN"
