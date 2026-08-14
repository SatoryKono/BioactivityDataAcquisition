---
record_id: browse-runs-8743-8744
record_type: working
repo_id: bioactivitydataacquisition
git_commit: b5347e37a422aae5d62f229ed0a6869cca7a9269
branch: fix/coderabbit-project-cycle-cr001
worktree_id: b5393af69d37a674
task_id: browse-runs-8743-8744
actor:
  runtime: grok
  agent: grok-4.6
  model: null
created_at: '2026-08-14T05:43:53.934652+00:00'
source_refs:
- <add-source-ref>
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 344050acb93fd054b721f61d1a9acf911755f307e2011d7583f73eace863622d
id: browse-runs-8743-8744
title: Stream A Browse-Runs live data plane 8743/8744
ttl_days: 14
confidence: episodic
summary: 'A1 fail-closed identity already on origin/main; 39 unit tests passed; live
  foreign root unhealthy then writer aligned 876cef27. A2 cutover without down -v
  or .env: new chembl_assay run 38bd461f written into mounted reports and visible
  on Ops panel 3010; verify_report_bind passed assay/target/publication. Closed #8744
  and #8743. Tracker #8741 left open pending B3 #8755. Monitoring Grafana still on
  run-explorer-8741 worktree (pre-existing).'
---

# Episodic summary

## Task

- Title: Stream A Browse-Runs live data plane 8743/8744

## Outcome

- A1 fail-closed identity already on origin/main; 39 unit tests passed; live foreign root unhealthy then writer aligned 876cef27. A2 cutover without down -v or .env: new chembl_assay run 38bd461f written into mounted reports and visible on Ops panel 3010; verify_report_bind passed assay/target/publication. Closed #8744 and #8743. Tracker #8741 left open pending B3 #8755. Monitoring Grafana still on run-explorer-8741 worktree (pre-existing).

## Lessons learned

- Replace with durable follow-up if needed
