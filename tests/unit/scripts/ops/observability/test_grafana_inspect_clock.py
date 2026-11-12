"""Inspect may expose epoch milliseconds while its cell shows a configured clock."""

import json
import subprocess

import pytest

pytestmark = pytest.mark.unit


def test_inspected_clock_requires_exact_configured_timezone_and_minute():
    program = """
const {inspectMatchesCell:m}=require('./scripts/ops/observability/grafana/capture_table_pages.cjs');
const check=(display,timeZone)=>m('1794419455358',display,{fieldFormats:[{unit:'time:YYYY-MM-DD HH:mm',timeZone}]});
process.stdout.write(JSON.stringify([
check('2026-11-11 17:50','UTC'),check('2026-11-11 20:50','Asia/Baghdad'),
check('2026-11-11 17:51','UTC'),check('2026-11-11 20:50','UTC'),
check('2026-11-11 17:50',undefined),check('2026-11-11 17:50','browser')]));
"""
    actual = json.loads(subprocess.check_output(["node", "-e", program], text=True))
    assert all(item["status"] == "VERIFIED_UNIT_FORMAT" for item in actual[:2])
    assert actual[2:] == [None] * 4


def test_empty_inspect_matches_only_explicit_field_no_value():
    program = """
const {inspectMatchesCell:m,collectValueMappings:c}=require('./scripts/ops/observability/grafana/capture_table_pages.cjs');
const valueMappings=c({overrides:[{properties:[{id:'noValue',value:'UNKNOWN'}]}]});
process.stdout.write(JSON.stringify([m('','UNKNOWN',{valueMappings}),m('','SUCCESS',{valueMappings}),m('','UNKNOWN',{})]));
"""
    actual = json.loads(subprocess.check_output(["node", "-e", program], text=True))
    assert actual[0]["status"] == "VERIFIED_VALUE_MAPPING"
    assert actual[1:] == [None, None]
