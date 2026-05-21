# 📚 BioETL Documentation Remediation Plan

## 🎯 Overview

This plan addresses GitHub issues #3088-3095 for comprehensive documentation improvements across the BioETL project. The remediation focuses on **documentation surface management, contract discoverability, governance drift, and quality reporting**.

## 🔍 Current State Analysis

### Documentation Structure
- **Total documentation files**: 1,238 markdown files
- **Active documentation**: `docs/00-05/` sections
- **Legacy/archive**: `docs/99-archive/` (50+ ADRs, legacy pipeline docs)
- **Generated reports**: Config discrepancies, comparison matrices
- **Excluded from publishing**: 40+ patterns in `mkdocs.yml`

### Identified Issues (from GitHub #3088-3095)

#### **#3095: Remediate active documentation surface, contract discoverability, and docs governance drift**
- **Priority**: Program-level
- **Scope**: Governance, surface management, discoverability
- **Impact**: High - affects developer onboarding and project maintainability

#### **#3094: Expose link-check results as a published docs quality report**
- **Priority**: P2
- **Scope**: CI/CD integration, quality reporting
- **Impact**: Medium - improves documentation reliability

#### **#3093: Add a docs-config parity gate for active entity configs and pipeline specs**
- **Priority**: P1
- **Scope**: Configuration management, parity checking
- **Impact**: High - prevents configuration drift

#### **#3092: Put legacy pipeline pages into redirect-or-notice mode**
- **Priority**: P1
- **Scope**: Legacy content management
- **Impact**: Medium - reduces confusion from outdated content

#### **#3091: Collapse Internal/Extended material behind a secondary navigation surface**
- **Priority**: P1
- **Scope**: Navigation restructuring
- **Impact**: High - improves user experience

#### **#3090: Generate ADR registry/status metadata in the project navigator**
- **Priority**: P1
- **Scope**: ADR management, navigation
- **Impact**: Medium - improves architectural transparency

#### **#3089: Publish DQ contracts as a first-class canonical contract surface**
- **Priority**: P0
- **Scope**: Data quality, contract publishing
- **Impact**: Very High - critical for data reliability

#### **#3088: Achieve pipeline-spec parity for all active unified entity configs**
- **Priority**: P0
- **Scope**: Pipeline configuration, parity
- **Impact**: Very High - ensures configuration consistency

## 📋 Detailed Remediation Plan

### Phase 1: Critical Remediation (P0 Issues - 2 weeks)

#### **Issue #3089: Publish DQ Contracts as First-Class Surface**
**Owner**: Data Quality Team
**Timeline**: Week 1-2

**Actions**:
1. **Inventory existing DQ contracts**
   - Audit `src/bioetl/domain/ports/quality/`
   - Catalog `tests/contract/` test suites
   - Document current contract locations

2. **Create canonical contract surface**
   - New section: `docs/04-reference/data-quality-contracts/`
   - Standardize contract documentation format
   - Include schema definitions, validation rules, examples

3. **Integrate with MkDocs navigation**
   - Add to main navigation under "Reference > Data Quality"
   - Create contract index page with search functionality
   - Add cross-references from pipeline documentation

4. **Automate contract documentation**
   - Script to extract contract metadata from code
   - Generate contract reference pages automatically
   - Integrate with CI/CD pipeline

**Deliverables**:
- ✅ Canonical DQ contract documentation section
- ✅ Automated contract reference generation
- ✅ Navigation integration
- ✅ Cross-references from pipelines

#### **Issue #3088: Achieve Pipeline-Spec Parity**
**Owner**: Pipeline Team
**Timeline**: Week 1-2

**Actions**:
1. **Analyze current discrepancies**
   - Review `docs/config-discrepancies-report.md`
   - Examine `docs/04-reference/config_comparison_matrix.csv`
   - Identify root causes of parity issues

2. **Create pipeline specification registry**
   - New section: `docs/04-reference/pipeline-specs/`
   - Standard template for pipeline documentation
   - Include: config parameters, data flow, dependencies

3. **Implement parity validation**
   - Script to validate config vs. documentation
   - CI/CD gate for parity checking
   - Automated discrepancy reporting

4. **Remediate critical discrepancies**
   - Focus on 26 active configs identified
   - Prioritize high-impact pipeline discrepancies
   - Create remediation backlog

**Deliverables**:
- ✅ Pipeline specification registry
- ✅ Parity validation script and CI gate
- ✅ Critical discrepancy remediation (top 5)
- ✅ Backlog for remaining issues

### Phase 2: High-Priority Remediation (P1 Issues - 3 weeks)

#### **Issue #3093: Docs-Config Parity Gate**
**Owner**: DevOps Team
**Timeline**: Week 3

**Actions**:
1. **Design parity gate architecture**
   - Define what constitutes "parity"
   - Establish acceptable thresholds
   - Design failure modes and reporting

2. **Implement CI/CD integration**
   - GitHub Actions workflow
   - Parity check on PRs and main branch
   - Configurable severity levels

3. **Create parity dashboard**
   - Visual representation of parity status
   - Historical trends
   - Drill-down to specific issues

**Deliverables**:
- ✅ CI/CD parity gate implementation
- ✅ Parity dashboard
- ✅ Documentation of parity requirements

#### **Issue #3092: Legacy Pipeline Redirect/Notice Mode**
**Owner**: Documentation Team
**Timeline**: Week 4

**Actions**:
1. **Inventory legacy pipeline documentation**
   - Identify outdated pipeline docs
   - Categorize by obsolescence level
   - Determine redirect vs. notice approach

2. **Implement redirect mechanism**
   - MkDocs redirect plugin configuration
   - Create redirect mapping
   - Test redirect functionality

3. **Add deprecation notices**
   - Standard notice template
   - Apply to legacy content
   - Update navigation to indicate legacy status

**Deliverables**:
- ✅ Legacy content inventory and categorization
- ✅ Redirect mechanism implementation
- ✅ Deprecation notices applied
- ✅ Updated navigation indicators

#### **Issue #3091: Internal/Extended Navigation Restructuring**
**Owner**: UX Team
**Timeline**: Week 5

**Actions**:
1. **Analyze current navigation structure**
   - Map existing navigation hierarchy
   - Identify internal vs. public content
   - Gather user feedback on pain points

2. **Design secondary navigation surface**
   - MkDocs theme configuration
   - Navigation tabs for different audiences
   - Clear labeling and organization

3. **Implement navigation changes**
   - Restructure `mkdocs.yml` navigation
   - Add audience indicators
   - Test navigation usability

**Deliverables**:
- ✅ Restructured navigation with clear audience separation
- ✅ Secondary navigation surface for internal/extended content
- ✅ Updated theme configuration
- ✅ Navigation usability testing results

#### **Issue #3090: ADR Registry/Status Metadata**
**Owner**: Architecture Team
**Timeline**: Week 5

**Actions**:
1. **Inventory existing ADRs**
   - Catalog 50+ existing ADRs
   - Extract metadata (status, date, owner)
   - Categorize by architectural area

2. **Create ADR registry**
   - New section: `docs/02-architecture/adr-registry/`
   - Standard metadata format
   - Search and filter functionality

3. **Integrate with project navigator**
   - Add ADR section to main navigation
   - Create status dashboard
   - Add cross-references from related documentation

**Deliverables**:
- ✅ ADR registry with metadata
- ✅ Navigation integration
- ✅ Status dashboard
- ✅ Cross-reference system

### Phase 3: Quality and Governance (P2 Issues - 2 weeks)

#### **Issue #3094: Link-Check Quality Reporting**
**Owner**: Quality Team
**Timeline**: Week 6

**Actions**:
1. **Enhance existing link checking**
   - Review `scripts/check_doc_links.py`
   - Improve error reporting
   - Add link categorization

2. **Create quality report format**
   - Standard report template
   - Include: broken links, redirect chains, external vs. internal
   - Add severity levels

3. **Publish quality reports**
   - CI/CD integration for report generation
   - Publish reports as documentation artifacts
   - Create historical trend analysis

**Deliverables**:
- ✅ Enhanced link checking script
- ✅ Quality report template and generation
- ✅ CI/CD integration
- ✅ Published quality reports

#### **Issue #3095: Documentation Governance**
**Owner**: Governance Team
**Timeline**: Week 7

**Actions**:
1. **Establish documentation governance framework**
   - Define roles and responsibilities
   - Create documentation lifecycle policy
   - Establish quality standards

2. **Implement governance tools**
   - Documentation linting and validation
   - Change control processes
   - Review workflows

3. **Create governance documentation**
   - Update `D-01 Governance & Style Guide.md`
   - Add documentation contribution guidelines
   - Create maintenance playbook

**Deliverables**:
- ✅ Documentation governance framework
- ✅ Governance tools and processes
- ✅ Updated governance documentation
- ✅ Contribution guidelines

## 📅 Timeline Summary

| Phase | Duration | Focus Areas | Key Deliverables |
|-------|----------|--------------|------------------|
| **1: Critical** | 2 weeks | P0 issues (#3088-3089) | DQ contracts, pipeline parity |
| **2: High-Priority** | 3 weeks | P1 issues (#3090-3093) | Navigation, ADRs, legacy content |
| **3: Quality** | 2 weeks | P2 issues (#3094-3095) | Link checking, governance |
| **Total** | 7 weeks | All issues | Comprehensive documentation remediation |

## 🎯 Success Metrics

### Quantitative Metrics
- **Pipeline parity**: 100% of active configs documented and validated
- **DQ contracts**: 100% of contracts published as canonical surface
- **ADR coverage**: 100% of ADRs in registry with metadata
- **Link quality**: <1% broken links in published documentation
- **Navigation satisfaction**: >90% positive feedback on new structure

### Qualitative Metrics
- **Developer onboarding time**: Reduced by 40%
- **Documentation findability**: Improved search and discovery
- **Content freshness**: Regular updates and maintenance
- **Governance compliance**: Consistent documentation quality

## 🛠️ Implementation Approach

### Tools and Technologies
- **MkDocs**: Documentation publishing platform
- **Material for MkDocs**: Theme with navigation features
- **GitHub Actions**: CI/CD for documentation quality gates
- **Python scripts**: Automation for parity checking, link validation
- **Pandoc/Markdown**: Content processing and conversion

### Team Structure
- **Documentation Lead**: Overall coordination
- **Content Team**: Writing and editing
- **DevOps Team**: CI/CD integration
- **Quality Team**: Testing and validation
- **Architecture Team**: ADR management
- **Stakeholder Review**: Regular feedback sessions

### Risk Management
- **Scope creep**: Strict prioritization by GitHub issue priority
- **Tool limitations**: Early prototyping and validation
- **Content quality**: Peer review process
- **Adoption**: Training and documentation for new processes

## 📋 Next Steps

1. **Kickoff meeting**: Align stakeholders on plan and priorities
2. **Tool setup**: Configure MkDocs, CI/CD, and automation scripts
3. **Content inventory**: Complete audit of existing documentation
4. **Phase 1 execution**: Begin with P0 issues (#3088-3089)
5. **Weekly syncs**: Track progress and address blockers

## 🔗 References

- **GitHub Issues**: #3088-3095
- **Current Docs**: `docs/` directory
- **Configuration**: `mkdocs.yml`
- **Discrepancy Reports**: `docs/config-discrepancies-report.md`
- **ADR Directory**: `docs/02-architecture/decisions/`

---

**Status**: Plan Approved ✅
**Next Review**: Weekly sync
**Owner**: Documentation Working Group
