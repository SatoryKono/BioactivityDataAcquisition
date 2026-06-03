---
id: docs-audit-p2-wave-1
title: 'P2 documentation audit: dashboard contract sheets completed'
task_id: docs-audit-p2-wave-1
created_at: '2026-06-03T06:55:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: "Successfully completed P2 documentation audit improvements for BioETL project.\n\
  \nP2 Fixes (dashboard/testing docs audibility enhancement):\n1. README.md testing\
  \ wording analysis:\n   - Verified that tests/e2e/ directory exists with 28 actual\
  \ e2e test files\n   - Confirmed README.md description is accurate: e2e exists as\
  \ directory, not just marker-only suite\n   - No changes needed to README.md testing\
  \ wording\n\n2. Per-dashboard contract coverage analysis:\n   - Reviewed existing\
  \ dashboard documentation structure\n   - Found panel-title-inventory.md with basic\
  \ panel inventory by dashboard\n   - Found dashboard-checklist-per-dashboard.md\
  \ with detailed checklist\n   - Found navigation-links.yaml and selector-contracts.yaml\
  \ for navigation/selectors\n   - Identified gap: no machine-readable mapping of\
  \ dashboard\u2192panels/formulas/data sources for drift detection\n\n3. Created\
  \ machine-readable dashboard inventory:\n   - Created docs/03-guides/dashboards/contracts/dashboard-inventory.yaml\n\
  \   - Includes mapping for all 8 shipped dashboards:\n     * bioetl-control-plane-v1\
  \ (primary, nav_id: 0)\n     * bioetl-overview-v2 (primary, nav_id: 1)\n     * bioetl-runtime\
  \ (primary, nav_id: 2)\n     * bioetl-provider-health-v2 (primary, nav_id: 3)\n\
  \     * bioetl-dq-v2 (primary, nav_id: 4)\n     * bioetl-workflow-overview (primary,\
  \ nav_id: 5)\n     * bioetl-silver-reject-explorer (explorer, no nav_id)\n     *\
  \ bioetl-alerts-slo (alert_triage, no nav_id)\n   - Schema includes: UID, title,\
  \ family, navigation_id, data_sources, panel_count, key_panels, selector_variables\n\
  \   - Contract metadata with version, last_updated, source_files, governance rules\n\
  \n4. Updated dashboard docs index:\n   - Added dashboard-inventory.yaml reference\
  \ to docs/03-guides/dashboards/README.md\n   - Documented purpose: machine-readable\
  \ mapping for drift detection and audibility\n\nBenefits:\n- Future drift detection\
  \ can compare dashboard-inventory.yaml against actual JSON files\n- Auditors have\
  \ single source of truth for shipped dashboard structure\n- Governance rules documented\
  \ in contract metadata\n- Easier to track navigation bus membership and dashboard\
  \ families"
---

# Episodic summary

## Task

- Title: P2 documentation audit: dashboard contract sheets completed

## Outcome

- Successfully completed P2 documentation audit improvements for BioETL project.

P2 Fixes (dashboard/testing docs audibility enhancement):
1. README.md testing wording analysis:
   - Verified that tests/e2e/ directory exists with 28 actual e2e test files
   - Confirmed README.md description is accurate: e2e exists as directory, not just marker-only suite
   - No changes needed to README.md testing wording

2. Per-dashboard contract coverage analysis:
   - Reviewed existing dashboard documentation structure
   - Found panel-title-inventory.md with basic panel inventory by dashboard
   - Found dashboard-checklist-per-dashboard.md with detailed checklist
   - Found navigation-links.yaml and selector-contracts.yaml for navigation/selectors
   - Identified gap: no machine-readable mapping of dashboard→panels/formulas/data sources for drift detection

3. Created machine-readable dashboard inventory:
   - Created docs/03-guides/dashboards/contracts/dashboard-inventory.yaml
   - Includes mapping for all 8 shipped dashboards:
     * bioetl-control-plane-v1 (primary, nav_id: 0)
     * bioetl-overview-v2 (primary, nav_id: 1)
     * bioetl-runtime (primary, nav_id: 2)
     * bioetl-provider-health-v2 (primary, nav_id: 3)
     * bioetl-dq-v2 (primary, nav_id: 4)
     * bioetl-workflow-overview (primary, nav_id: 5)
     * bioetl-silver-reject-explorer (explorer, no nav_id)
     * bioetl-alerts-slo (alert_triage, no nav_id)
   - Schema includes: UID, title, family, navigation_id, data_sources, panel_count, key_panels, selector_variables
   - Contract metadata with version, last_updated, source_files, governance rules

4. Updated dashboard docs index:
   - Added dashboard-inventory.yaml reference to docs/03-guides/dashboards/README.md
   - Documented purpose: machine-readable mapping for drift detection and audibility

Benefits:
- Future drift detection can compare dashboard-inventory.yaml against actual JSON files
- Auditors have single source of truth for shipped dashboard structure
- Governance rules documented in contract metadata
- Easier to track navigation bus membership and dashboard families

## Lessons learned

- Replace with durable follow-up if needed
