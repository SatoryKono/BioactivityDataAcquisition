import ast
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT, 'tests/integration/test_grafana_config.py'), 'r') as f:
    source = f.read()
    lines = source.splitlines(keepends=True)

tree = ast.parse(source)

overview_funcs = {
    'test_overview_dashboard_contains_control_plane_and_lineage_metrics',
    'test_overview_dashboard_has_l0_primary_question',
    'test_overview_answer_row_has_max_seven_panels',
    'test_overview_has_system_status_panel',
    'test_overview_has_next_action_panel',
    'test_overview_does_not_render_yield_green_without_denominator',
    'test_overview_backlog_and_lag_panels_expose_stage',
    'test_critical_panels_expose_open_actionable_datalinks',
    'test_overview_handoff_cards_show_status_and_reason',
    'test_overview_no_duplicate_green_zero_cards',
    'test_overview_does_not_use_forensic_variables',
    'test_overview_no_distribution_pie_panels',
    'test_overview_summary_queries_use_range_semantics',
    'test_overview_links_are_target_scoped',
    'test_overview_contains_runtime_dq_provider_control_workflow_status_cards',
    'test_overview_dashboard_exposes_workflow_overview_handoff',
    'test_overview_dashboard_surfaces_backlog_and_stage_lag_metrics',
    'test_overview_failed_runs_uses_run_metric_and_selected_time_range',
    'test_overview_processing_volume_panel_splits_units',
}

lines_to_remove = set()
overview_lines = []

overview_nodes = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in overview_funcs:
        overview_nodes.append(node)

overview_nodes.sort(key=lambda n: n.lineno)

for node in overview_nodes:
    start = node.lineno - 1
    end = node.end_lineno
    for i in range(start, end):
        lines_to_remove.add(i)
    overview_lines.extend(lines[start:end])

# Write back original without overview tests
with open(os.path.join(ROOT, 'tests/integration/test_grafana_config.py'), 'w') as f:
    for i, line in enumerate(lines):
        if i not in lines_to_remove:
            f.write(line)

# Write new overview file
new_lines = [
    '"""Integration tests for Grafana overview dashboard configuration."""\n',
    '\n',
    'import json\n',
    'from pathlib import Path\n',
    '\n',
    'import pytest\n',
    '\n',
    'from tests.integration._grafana_test_support import (\n',
    '    get_dashboard_panels,\n',
    '    get_panel_expressions,\n',
    '    load_dashboard,\n',
    ')\n',
    '\n',
    'pytestmark = pytest.mark.integration\n',
    '\n',
] + overview_lines

with open(os.path.join(ROOT, 'tests/integration/test_grafana_overview_config.py'), 'w') as f:
    f.writelines(new_lines)

print(f'Removed {len(lines_to_remove)} lines from original')
print(f'Overview file has {len(overview_lines)} lines of code')
