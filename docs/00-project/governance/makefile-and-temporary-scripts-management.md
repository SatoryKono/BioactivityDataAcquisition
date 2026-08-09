______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Makefile and Temporary Scripts Management

## Purpose

This document defines the governance and lifecycle management for Makefile targets and temporary diagnostic scripts in the BioETL project.

## Scope

This policy applies to:
- Makefile targets and their maintenance
- Temporary diagnostic scripts in `scripts/temp/`
- Script lifecycle management and cleanup
- Makefile target documentation and validation

## Makefile Target Governance

### Target Categories

#### Development Targets
- `install` - Sync local development dependencies
- `test` - Run stable local tests with coverage
- `lint` - Run ruff and mypy checks
- `test-fast` - Run fast non-slow tests
- `test-coverage` - Run stable tests with canonical coverage gate
- `test-architecture` - Run architecture tests
- `test-unit` - Run unit tests
- `test-integration` - Run non-e2e integration tests

#### Quality Assurance Targets
- `qa-debt` - Run integral quality/debt gate
- `qa-arch-fast` - Run fast architecture checks
- `security-check` - Run security test suite
- `test-ci-local` - Run local CI-oriented test subset
- `test-confidence-local` - Run confidence tests (unit + architecture + contracts + coverage)

#### Devin CLI Targets
- `devin` - Launch Devin CLI with BioETL runtime config
- `devin-check` - Validate Devin auth, rules, skills, and MCP config
- `devin-mcp-start` - Start the optional daily shared MCP plane
- `devin-fix-bug` - Quick bug fix workflow
- `devin-add-feature` - Quick feature addition workflow
- `devin-update-docs` - Quick documentation update
- `devin-audit-config` - Quick config audit

#### DeepWiki Targets
- `deepwiki-backup` - Backup wiki files before regeneration
- `deepwiki-update` - Update DeepWiki files via MCP
- `deepwiki-validate` - Validate wiki files against canonical sources

#### Diagram Targets
- `render-diagrams` - Render SVG/PNG for all diagram sources
- `render-diagrams-svg` - Render SVG only (faster local loop)
- `render-diagrams-checks` - Run PR-profile diagram validation
- `render-diagrams-bundles` - Regenerate Markdown diagram bundles
- `render-diagrams-all` - Render artifacts and refresh bundles

#### Docker Targets
- `docker-check` - Check Docker installation
- `docker-build` - Build BioETL image
- `docker-start` - Start the main BioETL adjunct
- `docker-stop` - Stop main services
- `docker-logs` - View logs (all services)
- `docker-health` - Check service health
- `docker-clean` - Stop containers; preserve volumes/images

#### Cleanup Targets
- `clean` - Preview local cleanup targets
- `clean-all` - Apply all cleanup targets
- `clean-local-artifacts` - Apply local cleanup targets
- `clean-preflight` - Run release-preflight cleanup

### Target Maintenance

#### Documentation Requirements
- Each target must have a clear purpose documented in the help section
- Targets should be grouped logically by category
- Target names should use kebab-case
- Complex targets should have inline comments explaining key steps

#### Validation Requirements
- Targets should reference existing scripts in `scripts/`
- Script references should be validated for existence
- Obsolete targets should be removed or marked as deprecated
- Target dependencies should be minimal and necessary

#### Deprecation Process
1. Mark target as deprecated in help section
2. Add deprecation notice with alternative target
3. Set deprecation timeline (typically 2-3 months)
4. Remove target after deprecation period
5. Update documentation and references

## Temporary Scripts Management

### Temporary Scripts Directory

**Location:** `scripts/temp/`

**Purpose:** Store temporary diagnostic scripts with bounded lifecycles

**Access:** Not part of standard development workflow, used for specific diagnostic purposes

### Lifecycle Management

#### Script Classification

Temporary scripts are classified by:
- **Purpose:** Diagnostic, evidence collection, temporary tooling
- **Expiration Date:** Bounded lifecycle with explicit review date
- **Owner:** Team or individual responsible for cleanup
- **Next Step:** Consolidation into canonical surface or retirement

#### Lifecycle Stages

1. **Creation**
   - Script created for specific diagnostic purpose
   - Added to `scripts/temp/` with README documentation
   - Assigned expiration date and owner
   - Documented in scripts inventory manifest

2. **Active Use**
   - Script used for intended diagnostic purpose
   - Monitored for effectiveness and necessity
   - May be extended if still needed (with justification)

3. **Review**
   - At expiration date, review script necessity
   - Decide: consolidate into canonical surface OR retire
   - Update scripts inventory manifest accordingly

4. **Consolidation or Retirement**
   - **Consolidation:** Move to appropriate canonical location with proper integration
   - **Retirement:** Remove from repository after confirming no longer needed

#### Current Temporary Scripts

### basedpyright Diagnostic Scripts (Review by: 2026-09-30)

**Owner:** @bioetl-platform
**Purpose:** Temporary utilities for typing debt campaign evidence collection
**Next Step:** Consolidate into canonical QA report surface or retire after campaign closes

- `report_basedpyright_error_snapshot.py` - Generate shrink-only basedpyright product error snapshot
- `report_basedpyright_suppression_inventory.py` - Generate basedpyright suppression inventory
- `report_basedpyright_tests_snapshot.py` - Generate basedpyright test-snapshot for scripts/tests advisory
- `report_basedpyright_warning_snapshot.py` - Generate basedpyright warning snapshot

### Governance Requirements

#### Script Requirements
- Must have clear purpose documentation
- Must have explicit expiration date
- Must have assigned owner
- Must have documented next step
- Must not be referenced from Makefile or CI

#### Directory Requirements
- `scripts/temp/` must have README explaining purpose
- `scripts/temp/` must have `__init__.py` for package structure
- Scripts should be grouped by purpose/campaign
- Regular cleanup of expired scripts

#### Inventory Requirements
- Temporary scripts must be marked in scripts inventory manifest
- Status must be `temporary_diagnostic`
- Must include lifecycle_decision, review_by, and next_step fields
- Must be tracked for cleanup and consolidation

## Cleanup and Validation

### Automated Validation

#### Makefile Validation
- Check that all script references exist
- Validate target dependencies
- Check for orphaned targets
- Validate target naming conventions

#### Temporary Scripts Validation
- Check expiration dates against current date
- Alert for expired scripts requiring review
- Validate that temporary scripts are not referenced from CI
- Check for scripts past expiration without action

### Manual Cleanup

#### Monthly Review
- Review temporary scripts approaching expiration
- Update expiration dates if still needed (with justification)
- Consolidate or retire expired scripts
- Update scripts inventory manifest

#### Quarterly Review
- Review Makefile for obsolete targets
- Update target documentation
- Remove deprecated targets
- Validate target usage patterns

## Related Documents

- [Script Naming Conventions](script-naming-conventions.md) - Naming standards for scripts
- [Script Documentation Standards](script-documentation-standards.md) - Documentation standards for scripts
- [Script Testing Standards](script-testing-standards.md) - Testing standards for scripts
- [Scripts Inventory Audit](../../reports/scripts_inventory_audit_report.md) - Overall script inventory

## Revision History

- **2026-08-09:** Initial governance definition for Makefile and temporary scripts management
- **2026-08-09:** Moved 4 basedpyright diagnostic scripts to scripts/temp/ with bounded lifecycles
