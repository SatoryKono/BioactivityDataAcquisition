# Script Management Guides

This directory contains documentation and guides for managing the BioETL script inventory.

## Contents

### 📋 Script Analysis and Cleanup

- **[script-analysis-prompt.md](script-analysis-prompt.md)** - Comprehensive guide for analyzing scripts to identify obsolete, duplicate, and suboptimal scripts with systematic cleanup planning.

## Purpose

The script management guides provide:

1. **Systematic Analysis Methods** - Structured approaches for evaluating script quality and usage
1. **Cleanup Strategies** - Safe methods for removing technical debt
1. **Governance Patterns** - Best practices for script organization and maintenance
1. **Decision Frameworks** - Criteria for evaluating script health and cleanup priority

## Usage

### When to Use These Guides

- **Quarterly Script Audits** - Regular inventory reviews
- **New Script Creation** - Ensuring compliance with governance policies
- **Script Refactoring** - Improving existing script quality
- **Technical Debt Reduction** - Planning cleanup initiatives
- **Onboarding** - Understanding script management practices

### How to Use

1. **Start with Analysis**: Use `script-analysis-prompt.md` to evaluate current inventory
1. **Identify Issues**: Categorize scripts by obsolete/duplicate/suboptimal/governance
1. **Plan Actions**: Create phased cleanup plan based on risk assessment
1. **Implement**: Execute cleanup with proper validation
1. **Document**: Update inventory and lifecycle records

## Related Documentation

- **Script Catalog**: `scripts/engineering/repo/catalog.yaml` - Canonical script locations
- **Inventory Manifest**: `configs/quality/scripts_inventory_manifest.json` - Current inventory
- **Lifecycle Registry**: `configs/quality/scripts_lifecycle_registry.json` - Script lifecycle decisions
- **Governance Rules**: [`AGENTS.md`](../../../AGENTS.md) — AI runtime entry and governance links; normative stack index in [`docs/00-project/NORMATIVE_SOURCES.md`](../../00-project/NORMATIVE_SOURCES.md)

## Maintenance

**Review Cycle**: Quarterly
**Owner**: @bioetl-architecture
**Last Updated**: 2024-04-14

**Contributing**:

- Follow existing format and structure
- Update change log in documents
- Ensure cross-references are maintained
- Validate with current inventory data

## Quick Reference

### Common Commands

```bash
# Sync script inventory
python3 -m scripts.engineering.repo sync-inventory --write

# Check inventory health
python3 -m scripts.engineering.repo check-inventory --check

# Analyze script references
grep -r "scripts/" .github/workflows/ | sort | uniq -c

# Check script quality
shellcheck scripts/**/*.sh
pylint scripts/**/*.py
```

### Key Metrics

- **Total Scripts**: Check inventory manifest
- **Legacy Scripts**: Aim for \<10% of total
- **Duplicate Scripts**: Target 0%
- **Governance Compliance**: Target 100%

## Roadmap

### Upcoming Guides

- **Script Creation Guide** - Best practices for new scripts
- **Testing Strategies** - How to test different script types
- **Cross-Platform Patterns** - Managing Windows/Linux compatibility
- **Performance Optimization** - Best practices for script efficiency

### Planned Enhancements

- Add automated analysis tools
- Integrate with CI/CD pipelines
- Create interactive decision trees
- Add real-world examples and case studies

______________________________________________________________________

**Status**: Active
**Version**: 1.0
**License**: MIT
