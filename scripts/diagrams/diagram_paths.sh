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

if [[ -d "$DIAGRAM_ROOT/governance" ]]; then
  DIAGRAM_GOVERNANCE_DIR="$DIAGRAM_ROOT/governance"
else
  DIAGRAM_GOVERNANCE_DIR="$DIAGRAM_ROOT/docs"
fi

if [[ -d "$DIAGRAM_ROOT/tooling" ]]; then
  DIAGRAM_TOOLING_DIR="$DIAGRAM_ROOT/tooling"
else
  DIAGRAM_TOOLING_DIR="$DIAGRAM_ROOT"
fi

if [[ -d "$DIAGRAM_ROOT/manifests" ]]; then
  DIAGRAM_MANIFESTS_DIR="$DIAGRAM_ROOT/manifests"
else
  DIAGRAM_MANIFESTS_DIR="$DIAGRAM_ROOT"
fi

if [[ -f "$DIAGRAM_TOOLING_DIR/render.sh" ]]; then
  DIAGRAM_RENDER_SCRIPT="$DIAGRAM_TOOLING_DIR/render.sh"
else
  DIAGRAM_RENDER_SCRIPT="$DIAGRAM_ROOT/render.sh"
fi

if [[ -f "$DIAGRAM_MANIFESTS_DIR/quality-gates.txt" ]]; then
  DIAGRAM_QUALITY_MANIFEST="$DIAGRAM_MANIFESTS_DIR/quality-gates.txt"
else
  DIAGRAM_QUALITY_MANIFEST="$DIAGRAM_ROOT/manifests/quality-gates.txt"
fi

if [[ -f "$DIAGRAM_MANIFESTS_DIR/visual-smoke.txt" ]]; then
  DIAGRAM_VISUAL_MANIFEST="$DIAGRAM_MANIFESTS_DIR/visual-smoke.txt"
else
  DIAGRAM_VISUAL_MANIFEST="$DIAGRAM_ROOT/manifests/visual-smoke.txt"
fi

if [[ -f "$DIAGRAM_MANIFESTS_DIR/png-compatibility.txt" ]]; then
  DIAGRAM_PNG_COMPAT_MANIFEST="$DIAGRAM_MANIFESTS_DIR/png-compatibility.txt"
else
  DIAGRAM_PNG_COMPAT_MANIFEST="$DIAGRAM_ROOT/manifests/png-compatibility.txt"
fi

DIAGRAM_CLASS_SOURCE_DIR="$DIAGRAM_ROOT/class-diagrams"
DIAGRAM_CLASS_SVG_DIR="$DIAGRAM_CLASS_SOURCE_DIR/svg"
