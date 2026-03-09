#!/usr/bin/env bash
# Script to create GitHub issues from markdown files in this directory.
# Prerequisites: gh CLI authenticated (gh auth login)
#
# Usage: bash .github/issues/create-issues.sh

set -euo pipefail

REPO="SatoryKono/BioactivityDataAcquisition"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure required labels exist
ensure_label() {
  local name="$1" color="$2" description="${3:-}"
  if ! gh label list -R "$REPO" --json name -q ".[].name" | grep -qx "$name"; then
    echo "Creating label: $name"
    gh label create "$name" --color "$color" --description "$description" -R "$REPO" 2>/dev/null || true
  fi
}

# Ensure milestone exists
ensure_milestone() {
  local title="$1"
  if ! gh api "repos/$REPO/milestones" --jq '.[].title' | grep -qx "$title"; then
    echo "Creating milestone: $title"
    gh api "repos/$REPO/milestones" -f title="$title" -f state="open" >/dev/null
  fi
}

echo "=== Ensuring labels exist ==="
ensure_label "data-lineage"        "0E8A16" "Data lineage and provenance tracking"
ensure_label "reproducibility"     "5319E7" "Scientific reproducibility features"
ensure_label "schema-evolution"    "D93F0B" "Schema versioning and evolution"
ensure_label "developer-experience" "FBCA04" "Developer experience improvements"
ensure_label "breaking-changes"    "B60205" "Breaking changes to APIs or schemas"
# These should already exist:
# priority:critical, priority:high

echo "=== Ensuring milestone exists ==="
ensure_milestone "Data Governance v2"

MILESTONE_NUMBER=$(gh api "repos/$REPO/milestones" --jq '.[] | select(.title=="Data Governance v2") | .number')

echo "=== Creating Issue 1: Data Lineage Graph ==="
gh issue create -R "$REPO" \
  --title "Data Lineage Graph — трассируемость Gold-записей до исходного API-ответа" \
  --label "data-lineage,reproducibility,priority:critical" \
  --milestone "Data Governance v2" \
  --body-file "$SCRIPT_DIR/001-data-lineage-graph.md"

echo "=== Creating Issue 2: Schema Evolution Policy ==="
gh issue create -R "$REPO" \
  --title "Schema Evolution Policy — автоматизация backward-compatibility checks для Gold-схемы" \
  --label "schema-evolution,breaking-changes,developer-experience,priority:high" \
  --milestone "Data Governance v2" \
  --body-file "$SCRIPT_DIR/002-schema-evolution-policy.md"

echo "=== Done ==="
echo "Note: Issue 3 was not provided in the original request."
