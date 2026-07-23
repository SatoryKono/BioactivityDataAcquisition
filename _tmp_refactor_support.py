from pathlib import Path

path = Path("tests/integration/_grafana_test_support.py")
text = path.read_text(encoding="utf-8")

old_get = '''@cache
def get_all_valid_metric_names() -> set[str]:
    """Extract all valid Prometheus metric names including suffixes for histograms."""
    from bioetl.infrastructure.observability import metrics

    all_valid_names: set[str] = set()
    all_valid_names.add("ALERTS")

    for item_name in dir(metrics):
        item = getattr(metrics, item_name)
        if not hasattr(item, "_name"):
            continue
        base_name = item._name
        all_valid_names.add(base_name)
        all_valid_names.add(f"{base_name}_created")

        class_name = type(item).__name__
        if "Histogram" in class_name or "Summary" in class_name:
            all_valid_names.update(
                {
                    f"{base_name}_bucket",
                    f"{base_name}_sum",
                    f"{base_name}_count",
                }
            )
        elif "Counter" in class_name:
            all_valid_names.add(f"{base_name}_total")

    for rules_path in _PROMETHEUS_RULE_FILES:
        rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        for group in rules_payload.get("groups", []):
            for rule in group.get("rules", []):
                record_name = rule.get("record")
                if isinstance(record_name, str):
                    all_valid_names.add(record_name)

    return all_valid_names
'''

new_get = '''def _add_metric_name_suffixes(
    all_valid_names: set[str], *, base_name: str, class_name: str
) -> None:
    """Register base metric name plus Prometheus type suffixes."""
    all_valid_names.add(base_name)
    all_valid_names.add(f"{base_name}_created")
    if "Histogram" in class_name or "Summary" in class_name:
        all_valid_names.update(
            {
                f"{base_name}_bucket",
                f"{base_name}_sum",
                f"{base_name}_count",
            }
        )
        return
    if "Counter" in class_name:
        all_valid_names.add(f"{base_name}_total")


def _register_runtime_metric_names(all_valid_names: set[str]) -> None:
    from bioetl.infrastructure.observability import metrics

    for item_name in dir(metrics):
        item = getattr(metrics, item_name)
        if not hasattr(item, "_name"):
            continue
        _add_metric_name_suffixes(
            all_valid_names,
            base_name=item._name,
            class_name=type(item).__name__,
        )


def _register_group_recording_rule_names(
    all_valid_names: set[str], group: dict[str, Any]
) -> None:
    for rule in group.get("rules", []):
        record_name = rule.get("record")
        if isinstance(record_name, str):
            all_valid_names.add(record_name)


def _register_recording_rule_metric_names(all_valid_names: set[str]) -> None:
    for rules_path in _PROMETHEUS_RULE_FILES:
        rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        for group in rules_payload.get("groups", []):
            _register_group_recording_rule_names(all_valid_names, group)


@cache
def get_all_valid_metric_names() -> set[str]:
    """Extract all valid Prometheus metric names including suffixes for histograms."""
    all_valid_names: set[str] = {"ALERTS"}
    _register_runtime_metric_names(all_valid_names)
    _register_recording_rule_metric_names(all_valid_names)
    return all_valid_names
'''

old_reg = '''def _register_recording_rule_label_sets(
    label_sets: dict[str, frozenset[str]],
) -> None:
    for rules_path in _PROMETHEUS_RULE_FILES:
        rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        for group in rules_payload.get("groups", []):
            for rule in group.get("rules", []):
                record_name = rule.get("record")
                expr = rule.get("expr")
                if isinstance(record_name, str) and isinstance(expr, str):
                    static_labels = frozenset(
                        str(label_name)
                        for label_name in rule.get("labels", {})
                        if isinstance(label_name, str)
                    )
                    label_sets[record_name] = (
                        label_sets.get(record_name, frozenset())
                        | _recording_rule_labels(expr, label_sets)
                        | static_labels
                    )
'''

new_reg = '''def _static_labels_from_rule(rule: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        str(label_name)
        for label_name in rule.get("labels", {})
        if isinstance(label_name, str)
    )


def _apply_recording_rule_label_set(
    label_sets: dict[str, frozenset[str]], rule: dict[str, Any]
) -> None:
    record_name = rule.get("record")
    expr = rule.get("expr")
    if not isinstance(record_name, str) or not isinstance(expr, str):
        return
    label_sets[record_name] = (
        label_sets.get(record_name, frozenset())
        | _recording_rule_labels(expr, label_sets)
        | _static_labels_from_rule(rule)
    )


def _register_recording_rule_label_sets_from_file(
    label_sets: dict[str, frozenset[str]], rules_path: Path
) -> None:
    rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    for group in rules_payload.get("groups", []):
        for rule in group.get("rules", []):
            _apply_recording_rule_label_set(label_sets, rule)


def _register_recording_rule_label_sets(
    label_sets: dict[str, frozenset[str]],
) -> None:
    for rules_path in _PROMETHEUS_RULE_FILES:
        _register_recording_rule_label_sets_from_file(label_sets, rules_path)
'''

assert old_get in text, "old_get missing"
assert old_reg in text, "old_reg missing"
text = text.replace(old_get, new_get).replace(old_reg, new_reg)

# Replace assert contracts from operator through silver end (before _emit_sample)
start = text.index("def _assert_operator_context_shell_contract(")
end = text.index("\ndef _emit_sample_structured_log(")
contracts = r'''def _query_text(variable: dict[str, object] | None) -> str:
    if variable is None:
        return ""
    query = variable.get("query", {})
    if isinstance(query, dict):
        return str(query.get("query", "") or "")
    return ""


def _assert_workflow_context_variable(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    workflow_var = variable_map.get("workflow")
    assert workflow_var is not None, (
        f"Dashboard {dashboard_path.name} must define shared 'workflow' context"
    )
    assert "bioetl_workflow_universe" in _query_text(workflow_var), (
        f"Dashboard {dashboard_path.name} 'workflow' query must use workflow universe"
    )


def _assert_run_id_filter_options_url(query_url: str) -> None:
    assert "/ops/control-plane/filter-options" in query_url
    assert "dimension=run_id" in query_url
    assert "response_shape=list" in query_url
    assert "workflow=${workflow}" in query_url
    assert "pipeline=${pipeline}" in query_url
    assert "run_type=${run_type:csv}" in query_url


def _assert_run_id_infinity_shell(
    dashboard_path: Path, run_id_var: dict[str, object]
) -> None:
    assert run_id_var.get("type") == "query"
    assert run_id_var.get("datasource") == "Quarantine Explorer"
    assert run_id_var.get("includeAll") is False
    assert run_id_var.get("multi") is False
    run_id_query = run_id_var.get("query", {})
    assert isinstance(run_id_query, dict)
    assert run_id_query.get("queryType") == "infinity"
    assert run_id_query.get("refId") == "variable"
    infinity_query = run_id_query.get("infinityQuery", {})
    assert isinstance(infinity_query, dict)
    assert infinity_query.get("format") == "table"
    assert infinity_query.get("parser") == "backend"
    assert infinity_query.get("root_selector") == "$.items"
    assert infinity_query.get("url_options", {}).get("method") == "GET"
    _assert_run_id_filter_options_url(str(infinity_query.get("url", "")))


def _assert_operator_context_shell_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert shared context selectors without allowing Prometheus run_id use."""
    _assert_workflow_context_variable(dashboard_path, variable_map)
    run_id_var = variable_map.get("run_id")
    assert run_id_var is not None, (
        f"Dashboard {dashboard_path.name} must define shared 'run_id' identity context"
    )
    _assert_run_id_infinity_shell(dashboard_path, run_id_var)


def _assert_prom_datasource_object(
    dashboard_path: Path, variable_name: str, variable: dict[str, object]
) -> None:
    assert variable.get("datasource") == {
        "type": "prometheus",
        "uid": "prometheus",
    }, (
        f"Dashboard {dashboard_path.name} '{variable_name}' must use canonical "
        "Prometheus datasource object"
    )


def _assert_provider_health_pipeline_run_type(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    pipeline_var = variable_map.get("pipeline")
    assert pipeline_var is not None, (
        f"Dashboard {dashboard_path.name} must define shared 'pipeline' context"
    )
    assert "bioetl_overview_pipeline_run_type_universe" in _query_text(pipeline_var)

    run_type_var = variable_map.get("run_type")
    assert run_type_var is not None, (
        f"Dashboard {dashboard_path.name} must define shared 'run_type' context"
    )
    assert "bioetl_overview_pipeline_run_type_universe" in _query_text(run_type_var)


def _assert_provider_health_provider_var(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    provider_var = variable_map.get("provider")
    assert provider_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'provider' variable"
    )
    _assert_prom_datasource_object(dashboard_path, "provider", provider_var)
    assert "bioetl_provider_health_check_provider_universe_15m" in _query_text(
        provider_var
    ), (
        f"Dashboard {dashboard_path.name} 'provider' query must use "
        "the canonical provider-universe recording rule"
    )


def _assert_provider_health_adapter_var(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    adapter_var = variable_map.get("adapter")
    assert adapter_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'adapter' variable for "
        "circuit-breaker metrics"
    )
    _assert_prom_datasource_object(dashboard_path, "adapter", adapter_var)
    adapter_query_text = _query_text(adapter_var)
    assert "bioetl_circuit_breaker_state" in adapter_query_text, (
        f"Dashboard {dashboard_path.name} 'adapter' query must use "
        "circuit-breaker state metric"
    )
    assert "adapter" in adapter_query_text, (
        f"Dashboard {dashboard_path.name} 'adapter' query must select adapter label"
    )


def _assert_provider_health_variable_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert the variable contract for the provider health dashboard."""
    _assert_operator_context_shell_contract(dashboard_path, variable_map)
    _assert_provider_health_pipeline_run_type(dashboard_path, variable_map)
    _assert_provider_health_provider_var(dashboard_path, variable_map)
    _assert_provider_health_adapter_var(dashboard_path, variable_map)
    pipeline_context = variable_map.get("pipeline_context")
    assert pipeline_context is not None
    assert pipeline_context.get("hide") == 2


def _extract_infinity_query_url(variable: dict[str, object]) -> str:
    query = variable.get("query", {})
    if not isinstance(query, dict):
        return ""
    infinity_query = query.get("infinityQuery")
    if isinstance(infinity_query, dict):
        url = infinity_query.get("url", "")
        if isinstance(url, str):
            return url
    legacy_url = query.get("query", "")
    return legacy_url if isinstance(legacy_url, str) else ""


_SILVER_REJECT_ROOT_SELECTORS = {
    "run_type": "$.run_types",
    "reason_code": "$.reason_codes",
    "field": "$.fields",
    "quarantine_run_id": "$.run_ids",
}


def _assert_silver_reject_pipeline_var(
    dashboard_path: Path, pipeline_var: dict[str, object]
) -> None:
    assert pipeline_var.get("datasource") == "Prometheus", (
        f"Dashboard {dashboard_path.name} 'pipeline' must use Prometheus datasource"
    )
    assert "bioetl_records_processed_total" in _query_text(pipeline_var), (
        f"Dashboard {dashboard_path.name} 'pipeline' query must use "
        "bioetl_records_processed_total"
    )
    assert pipeline_var.get("includeAll") is False, (
        f"Dashboard {dashboard_path.name} 'pipeline' must disable All scope"
    )
    assert pipeline_var.get("multi") is False, (
        f"Dashboard {dashboard_path.name} 'pipeline' must be single-select"
    )


def _assert_silver_reject_infinity_query_block(
    dashboard_path: Path,
    variable_name: str,
    query: dict[str, object],
    variable: dict[str, object],
) -> None:
    infinity_query = query.get("infinityQuery", {})
    assert isinstance(infinity_query, dict), (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must define "
        "an infinityQuery block"
    )
    assert infinity_query.get("format") == "table", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must return "
        "a table for Grafana variable extraction"
    )
    assert infinity_query.get("parser") == "backend", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must use "
        "the backend parser"
    )
    expected_root_selector = _SILVER_REJECT_ROOT_SELECTORS[variable_name]
    assert infinity_query.get("root_selector") == expected_root_selector, (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must select "
        f"{expected_root_selector}"
    )
    assert infinity_query.get("url_options", {}).get("method") == "GET", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must use GET"
    )
    query_url = _extract_infinity_query_url(variable)
    assert "/ops/quarantine/filter-options" in query_url, (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must use "
        "/ops/quarantine/filter-options endpoint"
    )
    assert "pipeline=${pipeline:csv}" not in query_url, (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must pass "
        "one concrete pipeline value"
    )
    if variable_name == "quarantine_run_id":
        assert "dimension=run_id" in query_url, (
            f"Dashboard {dashboard_path.name} 'quarantine_run_id' must keep "
            "the backend run_id dimension"
        )


def _assert_silver_reject_infinity_variable(
    dashboard_path: Path,
    variable_name: str,
    variable: dict[str, object] | None,
) -> None:
    assert variable is not None, (
        f"Dashboard {dashboard_path.name} must define '{variable_name}' variable"
    )
    assert variable.get("datasource") == "Quarantine Explorer", (
        f"Dashboard {dashboard_path.name} '{variable_name}' must use "
        "Quarantine Explorer datasource"
    )
    query = variable.get("query", {})
    assert isinstance(query, dict), (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must be a "
        "structured Infinity variable query"
    )
    assert query.get("queryType") == "infinity", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must opt "
        "into Infinity CustomVariableSupport"
    )
    assert query.get("refId") == "variable", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must use "
        "the Infinity variable refId"
    )
    _assert_silver_reject_infinity_query_block(
        dashboard_path, variable_name, query, variable
    )


def _assert_silver_reject_explorer_variable_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert the variable contract for the silver reject explorer dashboard."""
    pipeline_var = variable_map.get("pipeline")
    assert pipeline_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'pipeline' variable"
    )
    _assert_silver_reject_pipeline_var(dashboard_path, pipeline_var)

    assert "workflow" not in variable_map, (
        f"Dashboard {dashboard_path.name} must not own shared 'workflow' context"
    )

    for variable_name in ("run_type", "reason_code", "field", "quarantine_run_id"):
        _assert_silver_reject_infinity_variable(
            dashboard_path, variable_name, variable_map.get(variable_name)
        )

    quarantine_run_id_var = variable_map["quarantine_run_id"]
    assert quarantine_run_id_var.get("includeAll") is False, (
        f"Dashboard {dashboard_path.name} 'quarantine_run_id' must disable All scope"
    )
    assert quarantine_run_id_var.get("multi") is False, (
        f"Dashboard {dashboard_path.name} 'quarantine_run_id' must stay bounded as single-select"
    )

    payload_hash_var = variable_map.get("payload_hash")
    assert payload_hash_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'payload_hash' variable"
    )
    assert payload_hash_var.get("type") == "textbox", (
        f"Dashboard {dashboard_path.name} 'payload_hash' must be a textbox"
    )

'''

# Keep standard variable contract that comes before operator
std_start = text.index("def _assert_standard_variable_contract(")
# operator starts later - standard stays
# Actually start was operator - but standard is before operator. Good.
text = text[:start] + contracts + text[end+1:]
path.write_text(text, encoding="utf-8")
print("wrote", path.stat().st_size)
print("has helpers", "_assert_run_id_filter_options_url" in path.read_text(encoding="utf-8"))
