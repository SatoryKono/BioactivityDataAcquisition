"""Evaluate saved contract exclusions against the configured pipeline limits."""

import json
from pathlib import Path

import yaml

from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader


def exclusion_quality_expression() -> str:
    """Build the browser JSONata expression using canonical DQ config resolution."""
    root = Path(__file__).resolve().parents[4] / "configs"
    loader = DQConfigLoader(root)
    limits = {}
    for path in sorted((root / "entities").glob("*/*.yaml")):
        entity = yaml.safe_load(path.read_text(encoding="utf-8"))
        pipeline = entity.get("pipeline", {}).get("pipeline_name")
        if not pipeline:
            continue
        config = loader.load(path.parent.name, path.stem)
        limits[pipeline] = [config.soft_fail_threshold, config.hard_fail_threshold]
    mapping = json.dumps(limits, separators=(",", ":"))
    return (
        f"($limits := {mapping}; "
        "$limit := $lookup($limits, identity.pipeline_name); "
        "$s := funnel[stage_id in ['bronze','silver','gold']]; "
        "$r := $s.removals[outcome='excluded_by_contract']; "
        "$base := $s[stage_id='bronze'].records_out; "
        "$known := $count($distinct($s.stage_id)) = 3 and $count($s) = 3 "
        "and $count($s[tracking='full' and $type(removals)='array']) = 3 "
        "and $count($r) = $count($r[$type(count)='number' ? "
        "count >= 0 and count=$floor(count) : false]) "
        "and ($type($base)='number' ? $base >= 0 and $base=$floor($base) : false) "
        "and $count($limit)=2; "
        "$n := $known ? $sum($append([0], $r.count)) : null; "
        "$known := $known and $n <= $base; "
        "$rate := $known ? ($base=0 ? 0 : $n/$base) : null; "
        "$status := $known ? ($rate >= $limit[1] ? 'ERROR' : "
        "$rate >= $limit[0] ? 'WARN' : 'OK') : 'UNKNOWN'; "
        "[{'status': $status, 'detail': ($known ? 'excluded ' & $string($round($rate*100,2)) & '%' "
        ": 'excluded UNKNOWN')}])"
    )
