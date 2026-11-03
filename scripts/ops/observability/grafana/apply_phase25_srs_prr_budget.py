#!/usr/bin/env python3
"""Apply Grafana Phase 2.5 SRS/PRR donor–consumer budget edits (rev7 §2.4–2.5).

Rewrites the five provisioned dashboard JSON files in place:

- Overview donor 9002 becomes a multi-section selected-run-status payload
  (presentation enrichment stays in Infinity UQL; Grafana transforms cannot
  express that JSONata). Consumers use ``-- Dashboard --`` and filter
  ``_bioetl_frame``.
- DQ / Incident / Control Plane follow the same donor pattern.
- Identity / stages copies become markdown handoffs per §2.4.
- Control Plane 9418 indexByName / hideFrom / self-link fixes (F-11/F-12).

Does not start Docker, touch ``.env``, or inflate tech-debt budgets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.ops.observability.grafana.render_nav_bus import write_dashboard_source

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"

OPS = {"type": "yesoreyeram-infinity-datasource", "uid": "bioetl-ops-http"}
DASH_DS = {"type": "datasource", "uid": "-- Dashboard --"}
MIXED_DS = {"type": "datasource", "uid": "-- Mixed --"}
SRS_URL = (
    "/ops/observability/selected-run-status"
    "?pipeline=${pipeline}&run_id=${run_id}"
    "&run_type=${run_type:csv}&workflow=${workflow:csv}"
)
FRAME = "_bioetl_frame"
VIEW_PANEL_TRUST_SELF = "viewPanel=9418"
VIEW_PANEL_TRUST_SIBLING = "viewPanel=9414"
_SELECT_RUN = "SELECT RUN"

OV_IDENTITY = (
    "/d/bioetl-overview-v2/2-overview"
    "?${workflow:queryparam}&${pipeline:queryparam}"
    "&${run_type:queryparam}&${run_id:queryparam}"
    "&viewPanel=9300&${__url_time_range}"
)
DQ_STAGES = (
    "/d/bioetl-dq-v2/5-data-quality"
    "?${workflow:queryparam}&${pipeline:queryparam}"
    "&${run_type:queryparam}&${run_id:queryparam}"
    "&viewPanel=9460&${__url_time_range}"
)


def _walk(panels: list[dict[str, Any]] | None):
    for panel in panels or []:
        yield panel
        yield from _walk(panel.get("panels"))


def _by_id(data: dict[str, Any], panel_id: int) -> dict[str, Any]:
    for panel in _walk(data.get("panels")):
        if panel.get("id") == panel_id:
            return panel
    raise KeyError(panel_id)


def _dash_target(donor_id: int) -> dict[str, Any]:
    return {
        "panelId": donor_id,
        "refId": "A",
        "withTransforms": False,
        "datasource": dict(DASH_DS),
    }


def _filter_frame(frame: str) -> dict[str, Any]:
    return {
        "id": "filterByValue",
        "options": {
            "type": "include",
            "match": "all",
            "filters": [
                {
                    "fieldName": FRAME,
                    "config": {"id": "equal", "options": {"value": frame}},
                }
            ],
        },
    }


def _prepend_frame_filter(panel: dict[str, Any], frame: str) -> None:
    transforms = list(panel.get("transformations") or [])
    transforms = [t for t in transforms if not _is_frame_filter(t)]
    panel["transformations"] = [_filter_frame(frame), *transforms]


def _is_frame_filter(transform: dict[str, Any]) -> bool:
    if transform.get("id") != "filterByValue":
        return False
    filters = (transform.get("options") or {}).get("filters") or []
    return any(f.get("fieldName") == FRAME for f in filters)


def _project_fields(names: tuple[str, ...]) -> dict[str, Any]:
    """Keep only the named columns after a shared-donor frame filter."""
    return {
        "id": "filterFieldsByName",
        "options": {"include": {"names": list(names)}},
    }


def _ensure_field_projection(panel: dict[str, Any], names: tuple[str, ...]) -> None:
    """Insert/replace ``filterFieldsByName`` right after the frame row filter.

    Shared donors ship every section's columns on each row; ``filterByValue`` on
    ``_bioetl_frame`` keeps the right rows but leaves sibling-section fields on
    the table. Consumers that previously owned a dedicated Infinity target need
    an explicit column projection.
    """
    transforms = list(panel.get("transformations") or [])
    without = [t for t in transforms if t.get("id") != "filterFieldsByName"]
    insert_at = 0
    while insert_at < len(without) and _is_frame_filter(without[insert_at]):
        insert_at += 1
    without.insert(insert_at, _project_fields(names))
    panel["transformations"] = without


# Canonical column sets for identity / FK-scope / replay-check tables.
_IDENTITY_FIELDS = ("parameter", "value")
_RECONCILIATION_FIELDS = (
    "step_id",
    "mode",
    "scope",
    "pins",
    "limit",
    "result",
    "meaning",
)
_REPLAY_CHECK_FIELDS = ("code", "result", "reason", "evidence_ref")


def _infinity_uql(jsonata: str) -> dict[str, Any]:
    # Mirror historical Infinity shape: raw JSONata in root_selector and the
    # same expression wrapped for the UQL parser (tests assert on both).
    return {
        "refId": "A",
        "type": "json",
        "source": "url",
        "parser": "uql",
        "format": "table",
        "root_selector": jsonata,
        "url": SRS_URL,
        "url_options": {"method": "GET", "data": ""},
        "uql": f'parse-json | jsonata "{jsonata}"',
        "datasource": dict(OPS),
    }


def _tag_rows(expr: str, frame: str) -> str:
    """Wrap a JSONata array expression with ``_bioetl_frame`` on each row."""
    return f"$map({expr}, function($row){{$merge([$row, {{'{FRAME}': '{frame}'}}])}})"


# --- Overview multi-section JSONata (single SRS HTTP) ---------------------

_OV_DOMAINS = (
    "($s := presentation_summary[0]; "
    "$t := presentation_trust[0].trust_status; "
    "$r := presentation_trust[0].reasons_display; "
    "$issues := presentation_domains[verdict != 'OK' and verdict != 'N/A' "
    "and verdict != 'SELECT RUN' and verdict != 'НЕТ ЗАПУСКОВ']; "
    "$map(presentation_domains, function($d) { $merge([$d, {"
    "'status_display': ($d.domain = 'Workflow' or $d.domain = 'Provider') "
    "and $d.verdict = 'N/A' ? '—' : $d.verdict, "
    "'reason_display': $d.reason = 'cached_bronze_no_remote_probe' ? "
    "'Cached Bronze used; provider API was not called.' : $d.reason_display, "
    "'run_execution': $s.execution_state, "
    "'run_verdict': $s.verdict, "
    "'saved_trust': $t, "
    "'run_reason': $count($issues) > 0 ? $join($map($issues, function($d) { "
    "$d.domain & ': ' & ($d.reason = 'run_observation_missing' ? "
    "'Result not recorded' : $d.reason_display) }), '; ') : "
    "(($s.verdict = 'OK' or $s.verdict = 'SELECT RUN' or "
    "$s.verdict = 'НЕТ ЗАПУСКОВ') ? ($r ? $r : $s.reason) : $s.reason)"
    # f-string doubles braces; trailing `)` closes the outer `(` block.
    f", '{FRAME}': 'domains'}}]) }}))"
)

_OV_IDENTITY = (
    "($v := function($x){$exists($x) and $x != '' ? $string($x) : "
    "'Not recorded in saved run evidence'}; "
    "$s := summary[0]; "
    "$start := $s.started_at ? $toMillis($s.started_at) : null; "
    "$end := $s.completed_at ? $toMillis($s.completed_at) : null; "
    f"$map(["
    "{'parameter':'Run ID','value':$v(run_id)},"
    "{'parameter':'Pipeline','value':$v(pipeline)},"
    "{'parameter':'Run Type','value':$v(run_type)},"
    "{'parameter':'Started at','value':started_at ? "
    "$substring(started_at,0,10) & ' ' & $substring(started_at,11,5) & ' ' & "
    "($substring(started_at,-1) = 'Z' ? 'UTC' : $substring(started_at,-6)) : "
    "'Not recorded in saved run evidence'},"
    "{'parameter':'Total Run Duration','value':$start != null and $end != null "
    "and $end >= $start ? ($n := $floor(($end - $start) / 1000 + 0.5); "
    "$parts := [$floor($n / 86400), $floor(($n % 86400) / 3600), "
    "$floor(($n % 3600) / 60), $n % 60]; "
    "$units := [' d', ' h', ' min', ' s']; "
    "$n = 0 ? '0 s' : $join($map($parts, function($v, $i)"
    "{$v > 0 ? $string($v) & $units[$i]}), ' ')) : "
    "'Not recorded in saved run evidence'}"
    f"], function($row){{$merge([$row, {{'{FRAME}':'identity'}}])}}))"
)

_OV_PROVIDER = (
    "($d := presentation_domains[domain = 'Provider'][0]; "
    "$cached := $d.reason = 'cached_bronze_no_remote_probe'; "
    "$saved := evidence_availability in ['AVAILABLE', 'legacy_no_snapshot']; "
    "$completed := summary[0].completed_at; "
    "$age := $completed ? $floor(($millis() - $toMillis($completed)) / 1000) : null; "
    "$seconds := $age != null and $age>=0 ? $age : 0; "
    "$parts := [$floor($seconds/86400), $floor(($seconds%86400)/3600), "
    "$floor(($seconds%3600)/60)]; "
    "$units := [' d',' h',' min']; "
    "$elapsed := $join($map($parts,function($v,$i)"
    "{$v>0 ? $string($v)&$units[$i]}),' '); "
    "$map(provider_checks, function($p) { $merge([$p, {"
    "'data_source': $cached ? 'Cached Bronze' : ($p.data_source ? $p.data_source : "
    "($d.reason = 'run_preflight_provider_observation' and $p.evidence = 'PRESENT' "
    "? 'Provider check' : 'UNKNOWN')), "
    "'check_performed': $cached ? 'No' : ($p.evidence = 'PRESENT' ? 'Yes' : 'UNKNOWN'), "
    "'check_result_display': $cached ? '—' : ($p.evidence = 'PRESENT' and $p.check_result "
    "? $p.check_result : 'UNKNOWN'), "
    "'reason': $cached ? 'Cached Bronze used; provider API was not called.' : "
    "($d.reason = 'run_preflight_provider_observation' ? "
    "'Saved provider preflight check.' : "
    "($d.reason_display ? $d.reason_display : "
    "'Provider check evidence was not recorded.')), "
    "'observed_display': $age != null and $age >= 0 ? "
    "($age<60 ? 'Just now' : $elapsed & ' ago') : 'Not recorded', "
    "'report_label': $saved or $cached ? 'Open report' : '—'"
    # f-string doubles braces; trailing `)` closes the outer `(` block.
    f", '{FRAME}': 'provider'}}]) }}))"
)

_OV_STAGES = _tag_rows("stage_diagnostics", "stages")
_OV_RECON = _tag_rows("reconciliation_display", "reconciliation")
_OV_EXCL = (
    f"[{{'status': verdict='SELECT RUN' ? 'SELECT RUN' : contract_exclusions_status, "
    f"'detail': contract_exclusions_rate != null ? "
    f"'excluded ' & $string($round(contract_exclusions_rate*100,2)) & '%' : "
    f"(verdict='SELECT RUN' ? 'Choose a run' : 'excluded UNKNOWN'), "
    f"'{FRAME}': 'exclusions'}}]"
)


def _append_many(*parts: str) -> str:
    """Nest binary JSONata ``$append`` calls across many arrays."""
    if not parts:
        return "[]"
    expr = parts[0]
    for part in parts[1:]:
        expr = f"$append({expr}, {part})"
    return expr


_DONOR_SCHEMA = (
    "{"
    + ", ".join(
        f"'{field}': null"
        for field in (
            "_bioetl_frame",
            "domain",
            "verdict",
            "status",
            "detail",
            "reason",
            "reason_display",
            "status_display",
            "run_execution",
            "run_verdict",
            "saved_trust",
            "run_reason",
            "parameter",
            "value",
            "provider",
            "data_source",
            "check_performed",
            "check_result",
            "check_result_display",
            "evidence",
            "observed_at",
            "observed_display",
            "report_label",
            "stage_id",
            "stage_name",
            "tracking",
            "records_in",
            "records_out",
            "removals",
            "execution_state",
            "workflow",
            "pipeline",
            "run_type",
            "run_id",
            "started_at",
            "completed_at",
            "reasons_count",
            "reasons_display",
            "trust_status",
            "trust_reasons_action",
            "trust_action_note",
            "result",
            "check_id",
            "replay_ready",
            "readiness",
            "Run duration",
            "trust",
        )
    )
    + "}"
)


def _normalized_donor(*parts: str) -> str:
    """Give every donor row the same columns before Grafana builds a frame."""
    appended = _append_many(*parts)
    return (
        f"($schema := {_DONOR_SCHEMA}; "
        f"$map({appended}, function($row){{$merge([$schema, $row])}}))"
    )


_OV_DONOR = _normalized_donor(
    _OV_DOMAINS, _OV_IDENTITY, _OV_PROVIDER, _OV_STAGES, _OV_RECON, _OV_EXCL
)

_MERGED_PRR = (
    "($r := function($s,$o){$exists($s.removals[outcome=$o]) ? "
    "$sum($s.removals[outcome=$o].count) : ($s.tracking = 'full' ? 0 : null)}; "
    "$ratio := function($s,$n){$s.tracking='full' and $type($s.records_in)='number' "
    "and $type($n)='number' ? ($s.records_in>0 and $n>=0 and $n<=$s.records_in ? "
    "100*$n/$s.records_in : null) : null}; "
    "$map(funnel, function($s){($excluded := $s.tracking='full' and "
    "$type($s.removals)='array' ? $sum($append([0], "
    "$s.removals[outcome='excluded_by_contract'].count)) : null; "
    "{'stage_id':$s.stage_id, 'quarantined':$r($s,'quarantined'), "
    "'excluded':$r($s,'excluded_by_contract'), "
    "'deduplicated':$r($s,'deduplicated'), "
    "'filtered_out':$r($s,'filtered_out'), "
    "'excluded_pct':$ratio($s,$excluded), "
    "'saved_pct':$ratio($s,$s.records_out)})}))"
)

# --- DQ donor -------------------------------------------------------------

_DQ_STATUS = (
    "[$merge([presentation_summary[0], {"
    "'saved_trust': presentation_trust[0].trust_status, "
    "'reason_display': ($issues := presentation_domains[verdict != 'OK' and "
    "verdict != 'N/A' and verdict != 'SELECT RUN' and verdict != 'НЕТ ЗАПУСКОВ']; "
    "$count($issues) > 0 ? $join($map($issues, function($d) { "
    "$d.domain & ': ' & ($d.reason = 'run_observation_missing' ? "
    "'Result not recorded' : $d.reason_display) }), '; ') : "
    "((presentation_summary[0].verdict = 'OK' or "
    "presentation_summary[0].verdict = 'SELECT RUN' or "
    "presentation_summary[0].verdict = 'НЕТ ЗАПУСКОВ') ? "
    "(presentation_trust[0].reasons_display ? "
    "presentation_trust[0].reasons_display : presentation_summary[0].reason) : "
    f"presentation_summary[0].reason)), '{FRAME}': 'status'}}])]"
)

_DQ_DOMAINS = _tag_rows("presentation_domains", "domains")
_DQ_STAGES = (
    "($r := function($s,$o){$exists($s.removals[outcome=$o]) ? "
    "$sum($s.removals[outcome=$o].count) : ($s.tracking = 'full' ? 0 : null)}; "
    "$funnel := quality_evidence.funnel; "
    "$map(stage_diagnostics, function($d){($s := $funnel[stage_id=$d.stage_id][0]; "
    "$merge([$d, {"
    "'quarantined': $exists($s) ? $r($s,'quarantined') : null, "
    "'excluded': $exists($s) ? $r($s,'excluded_by_contract') : null, "
    "'deduplicated': $exists($s) ? $r($s,'deduplicated') : null, "
    "'filtered_out': $exists($s) ? $r($s,'filtered_out') : null, "
    + f"'{FRAME}': 'stages'"
    + "}]))}))"
)

_DQ_STAGEINPUT = (
    "($f := quality_evidence.funnel; "
    "$map(['01 bronze_records','02 silver_valid_records',"
    "'03 silver_filtered_out_records','04 silver_quarantined_records',"
    "'06 silver_deduplicated_records','07 gold_written_records',"
    "'08 gold_excluded_by_contract_records','09 gold_quarantined_records',"
    "'11 gold_deduplicated_records'], function($p) { "
    "($layerName := $contains($p, 'bronze') ? 'bronze' : "
    "($contains($p, 'silver') ? 'silver' : 'gold'); "
    "{'parameter': $p, 'count in': $f[stage_id = $layerName].records_in, "
    + f"'{FRAME}': 'stageinput'"
    + "}) }))"
)

_DQ_DONOR = _normalized_donor(_DQ_STATUS, _DQ_DOMAINS, _DQ_STAGES, _DQ_STAGEINPUT)

# --- Incident donor -------------------------------------------------------

_INC_STATUS = (
    "($issues := presentation_domains[verdict != 'OK' and verdict != 'N/A' "
    "and verdict != 'SELECT RUN' and verdict != 'НЕТ ЗАПУСКОВ']; "
    "[$merge([presentation_summary[0], {"
    "'saved_trust': presentation_trust[0].trust_status, "
    "'reason_display': $count($issues) > 0 ? $join($map($issues, function($d) { "
    "$d.domain & ': ' & ($d.reason = 'run_observation_missing' ? "
    "'Result not recorded' : $d.reason_display) }), '; ') : "
    "((presentation_summary[0].verdict = 'OK' or "
    "presentation_summary[0].verdict = 'SELECT RUN' or "
    "presentation_summary[0].verdict = 'НЕТ ЗАПУСКОВ') ? "
    "(presentation_trust[0].reasons_display ? "
    "presentation_trust[0].reasons_display : presentation_summary[0].reason) : "
    # Close merge object/array, status array, and the outer `($issues := …)` block.
    f"presentation_summary[0].reason), '{FRAME}': 'status'}}])])"
)

_INC_DOMAINS = _tag_rows("presentation_domains", "domains")
_INC_DURATION = (
    "($s := summary[0]; "
    "$start := $s.started_at ? $toMillis($s.started_at) : null; "
    "$end := $s.completed_at ? $toMillis($s.completed_at) : null; "
    f"[{{'Run duration': $start != null and $end != null and $end >= $start ? "
    f"($end - $start) / 1000 : null, '{FRAME}': 'duration'}}])"
)
_INC_DONOR = _normalized_donor(_INC_STATUS, _INC_DOMAINS, _INC_DURATION)

# --- Control Plane donor --------------------------------------------------

_CP_TRUST = (
    "[presentation_trust.($base := $sift($, function($v,$k)"
    "{$k != 'trust_reasons_action'}); $merge([$base, "
    "reasons_count > 0 ? {'trust_reasons_action':'View trust reasons'} : "
    "{'trust_action_note': reasons_count = 0 ? 'No trust issues' : 'Not assessed'}"
    f", {{'{FRAME}': 'trust'}}]))]"
)
_CP_REPLAY_READY = _tag_rows("replay_readiness", "replay_readiness")
_CP_REPLAY_CHECKS = (
    "$map(replay_checks^(result='fail' ? 0 : result='unknown' ? 1 : "
    "result='pass' ? 2 : 3), function($row){"
    f"$merge([$row, {{'{FRAME}': 'replay_checks'}}])}})"
)
_CP_DONOR = _normalized_donor(_CP_TRUST, _CP_REPLAY_READY, _CP_REPLAY_CHECKS)


def _advance_jsonata_string(expression: str, index: int) -> int:
    """Return the index after a single-quoted JSONata literal starting at ``index``."""
    escape = False
    cursor = index + 1
    while cursor < len(expression):
        char = expression[cursor]
        if escape:
            escape = False
        elif char == "\\":
            escape = True
        elif char == "'":
            return cursor + 1
        cursor += 1
    return len(expression)


_JSONATA_PAIRS = {")": "(", "]": "[", "}": "{"}
_JSONATA_OPENS = frozenset(_JSONATA_PAIRS.values())


def _consume_jsonata_bracket(stack: list[str], char: str) -> bool:
    """Update ``stack`` for one bracket char; False when unbalanced."""
    if char in _JSONATA_OPENS:
        stack.append(char)
        return True
    if char not in _JSONATA_PAIRS:
        return True
    if not stack or stack[-1] != _JSONATA_PAIRS[char]:
        return False
    stack.pop()
    return True


def _jsonata_brackets_balanced(expression: str) -> bool:
    """Return True when ``()[]{}`` are balanced outside single-quoted literals."""
    stack: list[str] = []
    index = 0
    while index < len(expression):
        char = expression[index]
        if char == "'":
            index = _advance_jsonata_string(expression, index)
            continue
        if not _consume_jsonata_bracket(stack, char):
            return False
        index += 1
    return not stack


def _assert_donor_jsonata_balanced() -> None:
    donors = {
        "_OV_DONOR": _OV_DONOR,
        "_DQ_DONOR": _DQ_DONOR,
        "_INC_DONOR": _INC_DONOR,
        "_CP_DONOR": _CP_DONOR,
        "_MERGED_PRR": _MERGED_PRR,
        "_OV_DOMAINS": _OV_DOMAINS,
        "_OV_PROVIDER": _OV_PROVIDER,
        "_DQ_STAGES": _DQ_STAGES,
        "_INC_STATUS": _INC_STATUS,
    }
    broken = [
        name for name, expr in donors.items() if not _jsonata_brackets_balanced(expr)
    ]
    if broken:
        raise ValueError(f"unbalanced JSONata donor expression(s): {', '.join(broken)}")


def _regex_pattern(item: Any) -> str | None:
    if not isinstance(item, dict) or item.get("type") != "regex":
        return None
    return str((item.get("options") or {}).get("pattern") or "")


def _value_mapping_options(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict) or item.get("type") != "value":
        return None
    options = item.get("options")
    return options if isinstance(options, dict) else None


def _ensure_exclusions_crit_color(panel: dict[str, Any]) -> None:
    """Canvas 9482 colors CRIT and keeps SELECT RUN distinct from UNKNOWN."""
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    mappings = list(defaults.get("mappings") or [])
    changed = False
    if not any(_regex_pattern(item) == "^CRIT.*" for item in mappings):
        insert_at = next(
            (
                index
                for index, item in enumerate(mappings)
                if (_regex_pattern(item) or "").startswith("^ERROR")
            ),
            len(mappings),
        )
        mappings.insert(
            insert_at,
            {
                "type": "regex",
                "options": {"pattern": "^CRIT.*", "result": {"color": "red"}},
            },
        )
        changed = True
    # No-selection must not reuse the UNKNOWN value map (Codex P2 #4449151423).
    select_run = {"text": _SELECT_RUN, "color": "gray"}
    value_maps = [
        (index, options)
        for index, item in enumerate(mappings)
        if (options := _value_mapping_options(item)) is not None
    ]
    if value_maps:
        index, options = value_maps[0]
        if options.get(_SELECT_RUN) != select_run:
            options = dict(options)
            options[_SELECT_RUN] = select_run
            mappings[index] = {"type": "value", "options": options}
            changed = True
    else:
        mappings.append({"type": "value", "options": {_SELECT_RUN: select_run}})
        changed = True
    if changed:
        defaults["mappings"] = mappings
    description = str(panel.get("description") or "")
    if "hard limit ERROR" in description:
        panel["description"] = description.replace(
            "hard limit ERROR", "hard limit CRIT"
        )


def _status_donor_transforms() -> list[dict[str, Any]]:
    """Shared Review Selected Run Status organize chain (DQ + Incident donors)."""
    return [
        _filter_frame("status"),
        {"id": "limit", "options": {"limitField": 1}},
        {
            "id": "filterFieldsByName",
            "options": {
                "include": {
                    "names": [
                        "execution_state",
                        "verdict",
                        "saved_trust",
                        "reason_display",
                    ]
                }
            },
        },
        {
            "id": "organize",
            "options": {
                "excludeByName": {},
                "indexByName": {
                    "execution_state": 0,
                    "verdict": 1,
                    "saved_trust": 2,
                    "reason_display": 3,
                },
                "renameByName": {
                    "execution_state": "Processing",
                    "verdict": "Overall verdict",
                    "saved_trust": "Trust",
                    "reason_display": "Reason",
                },
            },
        },
    ]


def _replace_with_handoff(
    panel: dict[str, Any],
    *,
    title: str,
    description: str,
    content: str,
) -> None:
    panel_id = panel["id"]
    grid = dict(panel["gridPos"])
    panel.clear()
    panel.update(
        {
            "id": panel_id,
            "type": "text",
            "title": title,
            "description": description,
            "gridPos": grid,
            "transparent": True,
            "options": {"mode": "markdown", "content": content},
        }
    )


def apply_overview(data: dict[str, Any]) -> None:
    donor = _by_id(data, 9002)
    donor["datasource"] = dict(OPS)
    donor["targets"] = [_infinity_uql(_OV_DONOR)]
    # Keep presentation columns available pre-transform for 9603/9604; donor
    # visual still filters to Domain/Status/Reason after the frame filter.
    donor["transformations"] = [
        _filter_frame("domains"),
        {"id": "limit", "options": {"limitField": 6}},
        {
            "id": "filterFieldsByName",
            "options": {
                "include": {"names": ["domain", "status_display", "reason_display"]}
            },
        },
        {
            "id": "organize",
            "options": {
                "indexByName": {
                    "domain": 0,
                    "status_display": 1,
                    "reason_display": 2,
                },
                "renameByName": {
                    "domain": "Domain",
                    "status_display": "Status",
                    "reason_display": "Reason",
                    "saved_trust": "Trust",
                },
            },
        },
    ]

    for pid, frame in (
        (9603, "domains"),
        (9604, "domains"),
        (9300, "identity"),
        (9480, "provider"),
        (9481, "provider"),
        (9482, "exclusions"),
        (9483, "reconciliation"),
    ):
        panel = _by_id(data, pid)
        panel["datasource"] = dict(DASH_DS)
        panel["targets"] = [_dash_target(9002)]
        _prepend_frame_filter(panel, frame)

    # Row filter alone is not enough: project back to the prior column set.
    _ensure_field_projection(_by_id(data, 9300), _IDENTITY_FIELDS)
    _ensure_field_projection(_by_id(data, 9483), _RECONCILIATION_FIELDS)
    recon = _by_id(data, 9483)
    if not any(t.get("id") == "organize" for t in recon.get("transformations") or []):
        recon.setdefault("transformations", []).append(
            {
                "id": "organize",
                "options": {
                    "indexByName": {
                        name: index for index, name in enumerate(_RECONCILIATION_FIELDS)
                    },
                    "renameByName": {
                        "step_id": "Workflow step",
                        "mode": "Mode",
                        "scope": "Row scope",
                        "pins": "Compared snapshots",
                        "limit": "Limit",
                        "result": "Result",
                        "meaning": "Interpretation",
                    },
                },
            }
        )

    _ensure_exclusions_crit_color(_by_id(data, 9482))

    stages = _by_id(data, 9460)
    # Mixed targets: Dashboard DS (stages rows from 9002) + one merged PRR.
    # Do not filter on ``_bioetl_frame`` alone — that would drop PRR rows.
    stages["datasource"] = dict(MIXED_DS)
    prr_url = (
        "/ops/observability/pipeline-run-report-artifact"
        "?pipeline=${selected_pipeline:percentencode}"
        "&run_id=${selected_run_id:percentencode}"
        "&format=pipeline_run_report_json"
    )
    stages["targets"] = [
        _dash_target(9002),
        {
            "refId": "B",
            "type": "json",
            "source": "url",
            "parser": "uql",
            "format": "table",
            "root_selector": "",
            "url": prr_url,
            "url_options": {"method": "GET", "data": ""},
            "uql": f'parse-json | jsonata "{_MERGED_PRR}"',
            "datasource": dict(OPS),
        },
    ]
    # Align with DQ 9460: drop extract exclude; keep canon fields (+ pct extras).
    stages["transformations"] = [
        {
            "id": "filterByValue",
            "options": {
                "type": "include",
                "match": "any",
                "filters": [
                    {
                        "fieldName": FRAME,
                        "config": {
                            "id": "equal",
                            "options": {"value": "stages"},
                        },
                    },
                    {
                        "fieldName": "stage_id",
                        "config": {"id": "isNotNull", "options": {}},
                    },
                ],
            },
        },
        {
            "id": "joinByField",
            "options": {"byField": "stage_id", "mode": "outerTabular"},
        },
        {"id": "limit", "options": {"limitField": 12}},
        {
            "id": "filterFieldsByName",
            "options": {
                "include": {
                    "names": [
                        "stage_id",
                        "state",
                        "reason",
                        "records_in",
                        "records_out",
                        "quarantined",
                        "excluded",
                        "deduplicated",
                        "filtered_out",
                        "duration_seconds",
                        "source",
                        "excluded_pct",
                        "saved_pct",
                    ]
                }
            },
        },
        {
            "id": "organize",
            "options": {
                "indexByName": {
                    "stage_id": 0,
                    "state": 1,
                    "reason": 2,
                    "records_in": 3,
                    "records_out": 4,
                    "quarantined": 5,
                    "excluded": 6,
                    "deduplicated": 7,
                    "filtered_out": 8,
                    "duration_seconds": 9,
                    "source": 10,
                    "excluded_pct": 11,
                    "saved_pct": 12,
                },
                "renameByName": {
                    "quarantined": "Quarantined",
                    "excluded": "Excluded",
                    "deduplicated": "Deduplicated",
                    "filtered_out": "Filtered out",
                },
                "excludeByName": {
                    "reason": True,
                    "source": True,
                    "Source": True,
                    "Evidence": True,
                },
            },
        },
    ]


def apply_dq(data: dict[str, Any]) -> None:
    donor = _by_id(data, 9406)
    donor["datasource"] = dict(OPS)
    donor["targets"] = [_infinity_uql(_DQ_DONOR)]
    donor["transformations"] = _status_donor_transforms()

    stages = _by_id(data, 9460)
    stages["datasource"] = dict(DASH_DS)
    stages["targets"] = [_dash_target(9406)]
    stages["transformations"] = [
        _filter_frame("stages"),
        {"id": "limit", "options": {"limitField": 12}},
        {
            "id": "filterFieldsByName",
            "options": {
                "include": {
                    "names": [
                        "stage_id",
                        "state",
                        "reason",
                        "records_in",
                        "records_out",
                        "quarantined",
                        "excluded",
                        "deduplicated",
                        "filtered_out",
                        "duration_seconds",
                        "source",
                    ]
                }
            },
        },
        {
            "id": "organize",
            "options": {
                "indexByName": {
                    "stage_id": 0,
                    "state": 1,
                    "reason": 2,
                    "records_in": 3,
                    "records_out": 4,
                    "quarantined": 5,
                    "excluded": 6,
                    "deduplicated": 7,
                    "filtered_out": 8,
                    "duration_seconds": 9,
                    "source": 10,
                },
                "renameByName": {
                    "quarantined": "Quarantined",
                    "excluded": "Excluded",
                    "deduplicated": "Deduplicated",
                    "filtered_out": "Filtered out",
                },
            },
        },
    ]

    domains = _by_id(data, 9451)
    domains["datasource"] = dict(DASH_DS)
    domains["targets"] = [_dash_target(9406)]
    _prepend_frame_filter(domains, "domains")

    processed = _by_id(data, 9403)
    # StageInput stays a dedicated Infinity target: a panel-level
    # ``_bioetl_frame`` filter would also drop processed-records rows from A.
    # Budget: donor 9406 = 1 SRS; StageInput reads pipeline-run-report funnel
    # (1 PRR) so removals stay available without a second SRS hop.
    targets = list(processed.get("targets") or [])
    new_targets = []
    for target in targets:
        if target.get("refId") == "StageInput":
            new_targets.append(
                {
                    "refId": "StageInput",
                    "type": "json",
                    "source": "url",
                    "parser": "uql",
                    "format": "table",
                    "root_selector": "",
                    "url": (
                        "/ops/observability/pipeline-run-report"
                        "?pipeline=${selected_pipeline}&run_id=${selected_run_id}"
                    ),
                    "url_options": {"method": "GET", "data": ""},
                    "uql": (
                        'parse-json | jsonata "'
                        "($f := funnel; "
                        "$map(['01 bronze_records','02 silver_valid_records',"
                        "'03 silver_filtered_out_records',"
                        "'04 silver_quarantined_records',"
                        "'06 silver_deduplicated_records',"
                        "'07 gold_written_records',"
                        "'08 gold_excluded_by_contract_records',"
                        "'09 gold_quarantined_records',"
                        "'11 gold_deduplicated_records'], function($p) { "
                        "($layerName := $contains($p, 'bronze') ? 'bronze' : "
                        "($contains($p, 'silver') ? 'silver' : 'gold'); "
                        "{'parameter': $p, "
                        "'count in': $f[stage_id = $layerName].records_in}) }))"
                        '"'
                    ),
                    "datasource": dict(OPS),
                }
            )
        else:
            new_targets.append(target)
    processed["targets"] = new_targets
    # Drop unused stageinput section from donor budget narrative; keep in donor
    # for optional future DS reuse without a third HTTP.

    _replace_with_handoff(
        _by_id(data, 9402),
        title="Inspect Run Identity",
        description=(
            "SELECTED RUN · Canonical run identity lives on Overview panel 9300. "
            "This panel is a handoff (rev7 §2.4); Control Plane 9408 remains "
            "out of scope."
        ),
        content=(
            "**Canonical identity:** [Open Review Run Identity on Overview]"
            f"({OV_IDENTITY})\n\n"
            "DQ no longer duplicates identity tables (F-16)."
        ),
    )
    _replace_with_handoff(
        _by_id(data, 9452),
        title="Inspect Selected Run Identity",
        description=("SELECTED RUN · Canonical identity is Overview 9300 (rev7 §2.4)."),
        content=(
            "**Canonical identity:** [Open Review Run Identity on Overview]"
            f"({OV_IDENTITY})"
        ),
    )


def apply_incident(data: dict[str, Any]) -> None:
    donor = _by_id(data, 2101)
    donor["datasource"] = dict(OPS)
    donor["targets"] = [_infinity_uql(_INC_DONOR)]
    donor["transformations"] = _status_donor_transforms()

    for pid, frame in ((9463, "duration"), (9451, "domains")):
        panel = _by_id(data, pid)
        panel["datasource"] = dict(DASH_DS)
        panel["targets"] = [_dash_target(2101)]
        _prepend_frame_filter(panel, frame)

    _replace_with_handoff(
        _by_id(data, 9460),
        title="Inspect Selected Run Stages",
        description=(
            "SELECTED RUN · Canonical stage table is DQ panel 9460 (rev7 §2.4)."
        ),
        content=(
            "**Canonical stages:** [Open Inspect Selected Run Stages on Data Quality]"
            f"({DQ_STAGES})"
        ),
    )
    _replace_with_handoff(
        _by_id(data, 9452),
        title="Inspect Selected Run Identity",
        description=("SELECTED RUN · Canonical identity is Overview 9300 (rev7 §2.4)."),
        content=(
            "**Canonical identity:** [Open Review Run Identity on Overview]"
            f"({OV_IDENTITY})"
        ),
    )


def _cp_trust_donor_transforms() -> list[dict[str, Any]]:
    return [
        _filter_frame("trust"),
        {
            "id": "convertFieldType",
            "options": {
                "conversions": [
                    {
                        "targetField": "evidence_observed_at",
                        "destinationType": "time",
                    }
                ]
            },
        },
        {
            "id": "filterFieldsByName",
            "options": {
                "include": {
                    "names": [
                        "processing_status",
                        "trust_status",
                        "reasons_display",
                        "reasons_text",
                        "evidence_observed_at",
                        "reasons_count",
                        "evidence_freshness",
                        "trust_reasons_action",
                        "trust_action_note",
                    ]
                }
            },
        },
        {
            "id": "organize",
            "options": {
                "indexByName": {
                    "processing_status": 0,
                    "trust_status": 1,
                    "reasons_display": 2,
                    "reasons_count": 3,
                    "trust_reasons_action": 4,
                    "trust_action_note": 5,
                    "evidence_observed_at": 6,
                    "evidence_freshness": 7,
                },
                "renameByName": {
                    "processing_status": "Processing result",
                    "trust_status": "Saved trust verdict",
                    "evidence_observed_at": "Assessed at",
                    "reasons_count": "Reason count",
                },
                "excludeByName": {"reasons_display": True},
            },
        },
        {"id": "limit", "options": {"limitField": 1}},
    ]


def _unhide_reasons_count(override: dict[str, Any]) -> None:
    props = [
        p for p in override.get("properties") or [] if p.get("id") != "custom.hideFrom"
    ]
    for prop in props:
        if prop.get("id") == "custom.hidden":
            prop["value"] = False
            break
    else:
        props.append({"id": "custom.hidden", "value": False})
    override["properties"] = props


def _fix_reasons_count_visibility(overrides: list[Any]) -> None:
    """Keep Reason count visible; drop conflicting hideFrom."""
    for override in overrides:
        name = (override.get("matcher") or {}).get("options")
        if name == "reasons_count":
            _unhide_reasons_count(override)


def _rewrite_link_urls(links: list[Any]) -> None:
    for link in links:
        if not isinstance(link, dict):
            continue
        url = link.get("url") or ""
        if VIEW_PANEL_TRUST_SELF in url:
            link["url"] = url.replace(VIEW_PANEL_TRUST_SELF, VIEW_PANEL_TRUST_SIBLING)


def _rewrite_trust_self_links(overrides: list[Any]) -> None:
    """Self-link viewPanel=9418 → 9414 on trust_reasons_action."""
    for override in overrides:
        for prop in override.get("properties") or []:
            if prop.get("id") == "links":
                _rewrite_link_urls(prop.get("value") or [])


def apply_control_plane(data: dict[str, Any]) -> None:
    donor = _by_id(data, 9418)
    donor["datasource"] = dict(OPS)
    donor["targets"] = [_infinity_uql(_CP_DONOR)]
    donor["transformations"] = _cp_trust_donor_transforms()

    overrides = donor.setdefault("fieldConfig", {}).setdefault("overrides", [])
    _fix_reasons_count_visibility(overrides)
    if VIEW_PANEL_TRUST_SELF in json.dumps(donor):
        _rewrite_trust_self_links(overrides)

    for pid, frame in ((9422, "replay_readiness"), (9423, "replay_checks")):
        panel = _by_id(data, pid)
        panel["datasource"] = dict(DASH_DS)
        panel["targets"] = [_dash_target(9418)]
        _prepend_frame_filter(panel, frame)

    _ensure_field_projection(_by_id(data, 9423), _REPLAY_CHECK_FIELDS)


def inventory(data: dict[str, Any]) -> tuple[int, int]:
    srs = prr = 0
    for panel in _walk(data.get("panels")):
        for target in panel.get("targets") or []:
            raw = json.dumps(target)
            if "selected-run-status" in raw:
                srs += 1
            if "pipeline-run-report" in raw:
                prr += 1
    return srs, prr


def main() -> None:
    try:
        _assert_donor_jsonata_balanced()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    files = {
        "bioetl-overview-v2.json": apply_overview,
        "bioetl-dq-v2.json": apply_dq,
        "bioetl-incident-v1.json": apply_incident,
        "bioetl-control-plane-v1.json": apply_control_plane,
    }
    print("Phase 2.5 SRS/PRR budget apply")
    for name, apply in files.items():
        path = DASH / name
        data = json.loads(path.read_text(encoding="utf-8"))
        before = inventory(data)
        apply(data)
        after = inventory(data)
        write_dashboard_source(
            path,
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            root=ROOT,
        )
        print(f"  {name}: SRS {before[0]}→{after[0]}  PRR {before[1]}→{after[1]}")

    # Run Explorer unchanged; still print budget line.
    re_path = DASH / "bioetl-run-explorer-v1.json"
    re_data = json.loads(re_path.read_text(encoding="utf-8"))
    print(f"  bioetl-run-explorer-v1.json: SRS/PRR {inventory(re_data)} (unchanged)")


if __name__ == "__main__":
    main()
