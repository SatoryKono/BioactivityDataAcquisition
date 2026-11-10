import os

path = 'scripts/engineering/ci/pr_lane_results.py'
with open(path, 'r') as f:
    content = f.read()

content = content.replace('    "scripts/ops/observability/grafana/dashboard_context_links.py": (\n        "tests/unit/scripts/ops/observability/test_dashboard_context_links.py",\n    ),', '    "scripts/ops/observability/grafana/dashboard_context_links.py": (\n        "tests/unit/scripts/ops/observability/test_dashboard_context_links.py",\n    ),\n    "docs/05-operations/runbooks/observability-checklist.md": (),\n    "grafana/README.md": (),')

with open(path, 'w') as f:
    f.write(content)
