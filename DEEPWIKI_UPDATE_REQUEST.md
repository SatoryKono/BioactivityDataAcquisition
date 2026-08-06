# Request for DeepWiki Regeneration

## Summary

Requesting manual regeneration of DeepWiki for repository `SatoryKono/BioactivityDataAcquisition` to sync with the updated documentation in `docs/`.

## Background

The repository documentation has been significantly updated with recent architectural changes, but DeepWiki needs to be regenerated to reflect these updates.

## Documentation Updates Completed

### 1. Monitoring Surface Reduction (2026-07-23)
- **Removed references to:** Loki, Promtail, Tempo, Quarantine Explorer UI
- **Updated files:**
  - `docs/05-operations/01-monitoring-guide.md`
  - `docs/05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md`
  - `docs/DOCKER_QUICKSTART.md`
- **Current stack:** Prometheus / Pushgateway / Grafana / image-renderer (opt-in only)

### 2. New ADRs Added (ADR-046 - ADR-055)
- **ADR-046:** Checkpoint Versus Ledger-Based Resume
- **ADR-047:** Workflow Control Plane for Declarative Workflows
- **ADR-048:** Domain Schema Boundary and Runtime Pandera Compatibility
- **ADR-049:** Context-Aware LOC Target Policy
- **ADR-050:** Silver Structural and Gold Semantic Filter Boundary
- **ADR-051:** QuarantineEntry Wide Constructor as Intentional Aggregate Surface
- **ADR-052:** Infrastructure Config Package Root as Permanent Public API
- **ADR-053:** Optional Grafana Scenes App Shell as Presentation Adapter
- **ADR-054:** Evidence-Backed Passport Documentation Projections
- **ADR-055:** Workflow Reconciliation Data-Step Ownership

**Registry updated:** `docs/02-architecture/adr-registry.md` (now contains 55 ADRs)

### 3. Control Plane Documentation
- **Updated files:**
  - `docs/03-guides/workflows.md` - workflow control plane commands
  - `docs/02-architecture/decisions/ADR-047-workflow-control-plane.md`
- **New CLI commands documented:**
  - `bioetl workflow run <name> --resume-last`
  - `bioetl workflow run <name> --repair-steps ...`
  - `bioetl workflow run <name> --force-steps ...`
  - `bioetl workflow status <name>`

### 4. Architecture Layer Refactoring
- **Updated files:**
  - `docs/02-architecture/02-application-layer.md`
  - `docs/04-reference/api/domain/ports.md`
- **New ports documented:**
  - `StorageMaintenancePort` (for `PostrunMetadataVersionResolver` refactoring)
  - `CompositeCheckpointPort` (for `CompositeCheckpointService` refactoring)
- **Narrow ports migration** documented

### 5. Publication Normalization Updates
- **Updated files:**
  - `docs/04-reference/normalization/publication-normalization.md`
  - `docs/04-reference/normalization/non-chembl-normalization-overview.md`
- **New canonical fields:**
  - `publication_type_unified`
  - `publication_subclass`
  - `publication_class`

### 6. AI Agent Subsystem Updates
- **Updated files:**
  - `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`
- **Claude runtime paths:** `.claude/**` marked as unavailable in current checkout
- **Canonical paths:** `ai/claude/*` for Claude runtime

### 7. Operational Documentation
- **Updated files:**
  - `docs/05-operations/runbooks/index.md`
  - `docs/05-operations/runbooks/workflow-control-plane.md`
- **Monitoring surface reduction** runbook added

## Current DeepWiki Status

Based on analysis, the current DeepWiki structure is:
- 9 main sections with good hierarchy
- 55 ADRs in registry (including latest ADR-046–055)
- Updated monitoring references (without Loki/Promtail/Tempo)
- Control Plane documentation with ADR-047

## Requested Action

Please regenerate DeepWiki for the repository to ensure it reflects all the documentation updates listed above. The `docs/` directory contains all the latest changes and should be used as the source of truth for the regeneration.

## Priority

**Medium** - Documentation is already up-to-date in the repository, this is a sync request to keep DeepWiki current.

## Verification

After regeneration, please verify:
- [ ] All 55 ADRs are reflected in DeepWiki
- [ ] Monitoring section no longer references Loki/Promtail/Tempo/Quarantine Explorer
- [ ] Control Plane section includes ADR-047 and new CLI commands
- [ ] Architecture sections reflect new ports (StorageMaintenancePort, CompositeCheckpointPort)
- [ ] Publication normalization includes new canonical fields
- [ ] AI Agent Subsystem reflects updated Claude runtime paths

## Additional Notes

- Branch `deepwiki-update-2026-08-05` was created for this work
- Documentation changes are already committed to the repository
- No code changes are required, only documentation sync

---

**Generated:** 2026-08-05
**Repository:** SatoryKono/BioactivityDataAcquisition
**Documentation path:** `docs/`