#!/usr/bin/env bash
set -euo pipefail

OWNER="${GITHUB_REPO_OWNER:-SatoryKono}"
REPO="${GITHUB_REPO_NAME:-BioactivityDataAcquisition}"
TOKEN_ENV="${GITHUB_TOKEN_ENV:-GITHUB_PERSONAL_ACCESS_TOKEN}"
API_BASE="https://api.github.com"

if [[ -z "${!TOKEN_ENV:-}" ]]; then
  echo "[FAIL] Missing GitHub token in ${TOKEN_ENV}" >&2
  exit 1
fi

TOKEN="${!TOKEN_ENV}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

COMMENT_2638="$(cat <<'EOF'
Closed as completed.

The repo now has a single published documentation verification entrypoint in
`docs/03-guides/docs-verification.md`.

Current published references already route there from the active docs surface,
including:
- `README.md`
- `docs/00-project/TOOLS.md`
- `docs/00-project/index.md`
- `docs/03-guides/index.md`
- `docs/03-guides/quick-start.md`
- `docs/03-guides/getting-started.md`

The guide includes a minimal flow, a fuller verification flow, mixed-environment
troubleshooting notes, and a doc-sync PR checklist. Repo-support references were
also cleaned up so active docs no longer point to a missing ad hoc verification
guide.

Verification note:
- `UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-links --links --specs --configs` -> PASS
EOF
)"

COMMENT_2639="$(cat <<'EOF'
Closed as completed.

Acceptance criteria are now covered by the active docs set:
- `reports/README.md` documents the working-output / shared-artefact /
  plan-bundle / trash / legacy-snapshot taxonomy.
- `docs/00-project/governance/01-documentation-governance-style-guide.md`
  states that `reports/**` is a repo-only supporting surface, not published
  guidance.
- `docs/03-guides/docs-verification.md` requires normative conclusions from
  `reports/**` to be migrated into `docs/00-05` before they are treated as
  guidance.
- Root-level `*_merged.md` files are explicitly classified as legacy snapshots.

Verification notes:
- `UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-links --links --specs --configs` -> PASS
- `UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-drift --ports --classes` -> PASS
EOF
)"

COMMENT_2640="$(cat <<'EOF'
Closed as completed.

`docs/03-guides/docs-verification.md` now contains a dedicated `Live Docs
Watchlist` section with all requested recurring audit targets:
- monitoring variables and dashboards
- control-plane contracts
- provider/entity inventory
- storage layout
- runbooks and operator procedures

Each watchlist item includes a source of truth, the docs to review, and a
concrete command/check to run. The guide also includes a doc-sync PR checklist
that points reviewers back to the watchlist.

Verification notes:
- `UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-links --links --specs --configs` -> PASS
- `UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-drift --ports --classes` -> PASS
EOF
)"

COMMENT_2643="$(cat <<'EOF'
Tracker synced on 2026-04-05.

Current status:
- `#2638` is complete: the published docs surface now routes documentation
  verification through `docs/03-guides/docs-verification.md`, and the guide
  contains the verification flow, troubleshooting notes, and a doc-sync PR
  checklist.
- `#2640` is complete: `docs/03-guides/docs-verification.md` includes the live
  watchlist with source-of-truth / docs-to-review / command-check entries.
- `#2639` is complete: `reports/README.md`, the governance guide, and the docs
  verification guide now align on the `reports/**` taxonomy and the repo-only
  vs published boundary.
- `#2637` remains the only open prerequisite in this tracker because the docs
  wrapper/toolchain path still needs a dedicated fix.

Verification notes from this pass:
- `UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-links --links --specs --configs` -> PASS
- `UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-drift --ports --classes` -> PASS
- strict build wrapper still belongs to `#2637` follow-up
EOF
)"

TRACKER_BODY="$(cat <<'EOF'
## Purpose
This tracking issue groups the foundational documentation-sync work identified
during the latest documentation cascade audit.

## Recommended execution order
1. #2637 — stabilize uv docs verification and add CI gate
2. #2638 — make docs-verification guide the single published entrypoint
3. #2640 — add live code-sync watchlist for recurring documentation audits
4. #2639 — define lightweight governance model for reports directory

## Notes
- #2637 remains the only open prerequisite in this bundle because the docs
  wrapper/toolchain path still needs a dedicated fix.
- #2638 is satisfied by the current published verification guide and active
  published references.
- #2640 is satisfied by the live watchlist and doc-sync PR checklist in
  `docs/03-guides/docs-verification.md`.
- #2639 is satisfied by the explicit `reports/**` governance model and
  published/repo-only boundary rules.

## Task checklist
- [ ] #2637
- [x] #2638
- [x] #2640
- [x] #2639

## Source
Derived from the documentation cascade audit and follow-up planning conducted on
2026-04-05.
EOF
)"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

api_call() {
  local method="$1"
  local path="$2"
  local payload="${3:-}"
  local body_file="$TMP_DIR/body.$RANDOM.json"
  local status

  if [[ -n "$payload" ]]; then
    status="$(
      curl -sS \
        -o "$body_file" \
        -w '%{http_code}' \
        -X "$method" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        -H "Content-Type: application/json" \
        "$API_BASE$path" \
        -d "$payload"
    )"
  else
    status="$(
      curl -sS \
        -o "$body_file" \
        -w '%{http_code}' \
        -X "$method" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "$API_BASE$path"
    )"
  fi

  echo "$status"
  cat "$body_file"
}

post_comment() {
  local issue_number="$1"
  local comment_text="$2"
  local payload
  payload="{\"body\":$(printf '%s' "$comment_text" | json_escape)}"
  mapfile -t response < <(api_call POST "/repos/$OWNER/$REPO/issues/$issue_number/comments" "$payload")
  if [[ "${response[0]}" =~ ^20[01]$ ]]; then
    echo "[OK] comment posted to #$issue_number"
  else
    echo "[WARN] failed to post comment to #$issue_number (HTTP ${response[0]})"
    printf '%s\n' "${response[@]:1}"
  fi
}

close_issue() {
  local issue_number="$1"
  mapfile -t response < <(api_call PATCH "/repos/$OWNER/$REPO/issues/$issue_number" '{"state":"closed"}')
  if [[ "${response[0]}" == "200" ]]; then
    echo "[OK] closed #$issue_number"
  else
    echo "[WARN] failed to close #$issue_number (HTTP ${response[0]})"
    printf '%s\n' "${response[@]:1}"
  fi
}

update_tracker_body() {
  local payload
  payload="{\"body\":$(printf '%s' "$TRACKER_BODY" | json_escape)}"
  mapfile -t response < <(api_call PATCH "/repos/$OWNER/$REPO/issues/2643" "$payload")
  if [[ "${response[0]}" == "200" ]]; then
    echo "[OK] updated tracker body for #2643"
  else
    echo "[WARN] failed to update tracker body for #2643 (HTTP ${response[0]})"
    printf '%s\n' "${response[@]:1}"
  fi
}

echo "Applying docs issue sync for $OWNER/$REPO"

post_comment 2638 "$COMMENT_2638"
post_comment 2639 "$COMMENT_2639"
post_comment 2640 "$COMMENT_2640"
post_comment 2643 "$COMMENT_2643"

close_issue 2638
close_issue 2639
close_issue 2640
update_tracker_body

echo "Done."
