#!/usr/bin/env bash
# Shared path helpers for BioETL diagram shell tooling.

if [[ -z "${REPO_ROOT:-}" ]]; then
  _DIAGRAM_PATHS_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if REPO_ROOT_GIT="$(git -C "$_DIAGRAM_PATHS_SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
    REPO_ROOT="$REPO_ROOT_GIT"
  else
    REPO_ROOT="$(cd "$_DIAGRAM_PATHS_SCRIPT_DIR/../.." && pwd)"
  fi
fi

ARCHITECTURE_DOCS_ROOT="$REPO_ROOT/docs/02-architecture"
if [[ -d "$ARCHITECTURE_DOCS_ROOT/diagrams" ]]; then
  DIAGRAM_ROOT="$ARCHITECTURE_DOCS_ROOT/diagrams"
else
  DIAGRAM_ROOT="$ARCHITECTURE_DOCS_ROOT/mmd-diagrams"
fi

DIAGRAM_ROOT_REL="${DIAGRAM_ROOT#$REPO_ROOT/}"
DIAGRAM_THEME_DIR="$DIAGRAM_ROOT/theme"
DIAGRAM_RENDER_SCRIPT="$DIAGRAM_ROOT/render.sh"
DIAGRAM_QUALITY_MANIFEST="$DIAGRAM_ROOT/quality-gate-manifest.txt"
DIAGRAM_VISUAL_MANIFEST="$DIAGRAM_ROOT/visual-smoke-manifest.txt"
DIAGRAM_CLASS_SOURCE_DIR="$DIAGRAM_ROOT/class-diagrams"
DIAGRAM_CLASS_SVG_DIR="$DIAGRAM_CLASS_SOURCE_DIR/svg"
