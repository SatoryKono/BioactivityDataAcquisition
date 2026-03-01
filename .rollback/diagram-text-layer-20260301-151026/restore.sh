#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cp -f "$REPO_ROOT/.rollback/diagram-text-layer-20260301-151026/docs/02-architecture/mmd-diagrams/render.sh" "$REPO_ROOT/docs/02-architecture/mmd-diagrams/render.sh"
cp -f "$REPO_ROOT/.rollback/diagram-text-layer-20260301-151026/docs/02-architecture/mmd-diagrams/README.md" "$REPO_ROOT/docs/02-architecture/mmd-diagrams/README.md"
cp -f "$REPO_ROOT/.rollback/diagram-text-layer-20260301-151026/scripts/run_diagram_checks.sh" "$REPO_ROOT/scripts/run_diagram_checks.sh"
cp -f "$REPO_ROOT/.rollback/diagram-text-layer-20260301-151026/tests/architecture/test_run_diagram_checks_script.py" "$REPO_ROOT/tests/architecture/test_run_diagram_checks_script.py"
rm -f "$REPO_ROOT/scripts/strip_svg_foreign_object.py"
rm -f "$REPO_ROOT/tests/architecture/test_strip_svg_foreign_object.py"
echo "Rollback restored from .rollback/diagram-text-layer-20260301-151026"
