# Cross-Synthesis: documentation-internal-surface-governance

Дата: 2026-03-27

## Consolidated interpretation

The 2026-03-27 refresh changes one important part of the earlier interpretation:
the project no longer operates with a broad internal-published publication model
for `plans/**` and `reports/**`. Instead, it now uses a stricter split between
published docs and repo-only reference surfaces. Current evidence supports four
narrow governance conclusions.

### 1. AI top-level docs remain discoverable enough without nav promotion

`docs/00-project/ai/README.md` is still intentionally handled as a repository
path entrypoint from the project hub rather than a primary nav section. The
strongest remaining argument for nav promotion is convenience, not correctness.

Supporting evidence:

- `EV-documentation-internal-surface-governance-ai-index-is-coherent-but-link-only`
- `EV-documentation-internal-surface-governance-project-index-routes-readers-to-repo-only-surfaces`

### 2. `plans/**` and `reports/**` are now governed as repo-only reference surfaces

The governing model is now stricter than the 2026-03-23 snapshot: `plans/**`
and `reports/**` are explicitly `internal + repo-only`, and `mkdocs.yml`
excludes them from publication. Discoverability is preserved by curated
repository-path references from the published hub pages.

Supporting evidence:

- `EV-documentation-internal-surface-governance-plans-and-reports-are-now-repo-only-by-policy`
- `EV-documentation-internal-surface-governance-project-index-routes-readers-to-repo-only-surfaces`

### 3. The current factual doc-sync wave is closed and enforced through guards

The current tree is green under the active documentation guard layer. Link and
drift checks pass, strict MkDocs build remains green, and the experimental
deployment docs are aligned with the helper script's current override model.

Supporting evidence:

- `EV-documentation-internal-surface-governance-doc-guards-confirm-current-sync-health`
- `EV-documentation-internal-surface-governance-strict-mkdocs-build-remains-green-under-current-boundary`
- `EV-documentation-internal-surface-governance-deployment-docs-match-helper-overrides`

### 4. Mixed RU/EN style remains a secondary readability issue

The mixed-language pattern is still visible, but the evidence still does not
support treating it as a governance failure. A large normalization pass would
create more churn than value right now.

Supporting evidence:

- `EV-documentation-internal-surface-governance-mixed-language-is-readability-debt`

## Decision candidates

1. Keep `docs/00-project/ai/README.md` as a curated repository-path entrypoint
   for now, rather than promote it into nav immediately.
1. Treat `plans/**` and `reports/**` as repo-only reference surfaces and point
   to them from published docs via repository paths or curated summaries.
1. Keep documentation governance in the guard layer unless a future green
   baseline breaks again.
1. Defer dedicated RU/EN normalization; allow opportunistic cleanup when
   touching internal docs for other reasons.
