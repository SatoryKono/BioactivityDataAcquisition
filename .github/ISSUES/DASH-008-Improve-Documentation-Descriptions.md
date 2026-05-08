# Improve Documentation and Panel Descriptions Across All Dashboards

**Status**: Open
**Priority**: P2 (Medium)
**Labels**: `dashboard`, `documentation`, `UX`, `maintainability`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards lack comprehensive documentation and consistent panel descriptions. Some dashboards have reading guides while others don't, panel description formats vary, and the scope of each dashboard (current status vs selected-range evidence) is not clearly documented.

## 🔍 Root Cause Analysis

1. **No Reading Guides**: Most dashboards lack quick-start guides
2. **Inconsistent Descriptions**: Panel description format varies across dashboards
3. **Missing Scope Documentation**: Not clear what each dashboard shows (current vs historical)
4. **Inconsistent Runbook Links**: Some panels have runbook links, others don't
5. **No Dashboard Guide**: No comprehensive guide for using the dashboard suite

## 📋 Scope

**Affected Components:**

- All dashboard JSON descriptions
- Panel-level descriptions
- Dashboard-level documentation
- Runbook links
- Dashboard guide documentation

**Impact Analysis:**

```bash
# Count description inconsistencies
grep -rn "description" grafana/dashboards/*.json | wc -l

# Check for reading guides
grep -rn "reading.*guide\|First action" grafana/dashboards/*.json
```

## 🎯 Solution Plan

### Phase 1: Define Documentation Standards (1 day)

1. **Establish Description Format**

   ```yaml
   # Description format standards
   panel_description:
     structure: |
       What the panel shows
       Time scope (current vs range)
       Key thresholds or mappings
       Next action or interpretation
   
   dashboard_description:
     structure: |
       Primary question the dashboard answers
       Scope and variables
       Current vs range evidence distinction
       When to use this dashboard
   ```

1. **Define Reading Guide Template**

   ```markdown
   # Reading guide template
   ## Dashboard Name
   
   ### Primary Question
   [What this dashboard answers]
   
   ### Scope
   [Variables and their impact]
   
   ### Reading Guide
   [How to interpret the dashboard]
   
   ### Next Actions
   [When to drill down to other dashboards]
   ```

1. **Define Runbook Link Standards**

   ```yaml
   # Runbook link standards
   required_for:
     - current_status_panels
     - error_panels
     - blocker_panels
   
   link_format: https://github.com/.../docs/05-operations/runbooks/{runbook}.md
   ```

### Phase 2: Add Reading Guides (2 days)

1. **Add Reading Guides to All Dashboards**

   ```json
   // Add as text panel at top
   {
     "type": "text",
     "options": {
       "content": "<div style='padding:10px;background:rgba(255,152,48,0.08);'>
         <h3>Reading Guide</h3>
         <p>Primary question: ...</p>
         <p>Scope: ...</p>
         <p>Reading guide: ...</p>
       </div>"
     }
   }
   ```

1. **Apply to All Dashboards**

   - bioetl-control-plane-v1.json ✅
   - bioetl-overview-v2.json ✅ (partial guide exists)
   - bioetl-runtime.json ✅ (partial guide exists)
   - bioetl-provider-health-v2.json ✅
   - bioetl-dq-v2.json ✅
   - bioetl-workflow-overview.json ✅
   - bioetl-silver-reject-explorer.json ✅

### Phase 3: Standardize Panel Descriptions (2 days)

1. **Update Panel Descriptions**

   ```json
   // Standard panel description
   {
     "description": "What this panel shows. Time scope: [current/range]. Thresholds: [values]. Next action: [guidance]."
   }
   ```

1. **Add Runbook Links**

   ```json
   // Add runbook links to appropriate panels
   {
     "dataLinks": [
       {
         "title": "Open Runbook",
         "url": "https://github.com/.../runbook.md",
         "targetBlank": true
       }
     ]
   }
   ```

1. **Document Dashboard Scope**

   ```json
   // Add to dashboard-level description
   {
     "description": "Primary question: ... Scope: current vs range evidence. Variables: ..."
   }
   ```

### Phase 4: Create Dashboard Guide (1 day)

1. **Create Comprehensive Guide**

   ```markdown
   # docs/05-operations/grafana-dashboard-guide.md
   ## Grafana Dashboard Suite Guide
   
   ### Dashboard Overview
   [List all dashboards and their purposes]
   
   ### Navigation Flow
   [How to navigate between dashboards]
   
   ### Variable Reference
   [Link to variable reference]
   
   ### Common Patterns
   [Standard patterns across dashboards]
   
   ### Troubleshooting
   [Common issues and solutions]
   ```

## ✅ Success Criteria

- [ ] All dashboards have reading guides
- [ ] Panel descriptions follow standard format
- [ ] Dashboard scope documented
- [ ] Runbook links added to appropriate panels
- [ ] Comprehensive dashboard guide created
- [ ] Documentation published

## 📊 Verification Commands

```bash
# Verify reading guides exist
grep -rn "Reading Guide\|reading.*guide" grafana/dashboards/*.json

# Check panel descriptions
jq '.panels[].description' grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Usability**: Clear guidance for using dashboards
- **Consistency**: Uniform description format
- **Efficiency**: Faster troubleshooting with runbook links
- **Onboarding**: Easier for new operators

### Potential Risks

- **Documentation Maintenance**: Need to keep docs updated
- **Clutter**: Reading guides may take up screen space
- **Link Rot**: Runbook links may break

### Mitigation Strategies

- **Concise Guides**: Keep reading guides brief and focused
- **Collapsible**: Make guides collapsible if needed
- **Link Validation**: Script to check runbook links
- **Regular Reviews**: Schedule documentation reviews

## 🎯 Related Issues

- **Depends On**: DASH-001 (Navigation), DASH-006 (Variables)
- **Related To**: All DASH-* issues

## ⏳ Time Estimate

**Total**: 6 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-16

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Description format standards defined
- [ ] Reading guide template created
- [ ] Runbook link standards established
- [ ] Reading guides added to all dashboards
- [ ] Panel descriptions standardized
- [ ] Runbook links added to appropriate panels
- [ ] Dashboard scope documented
- [ ] Comprehensive dashboard guide created
- [ ] Documentation reviewed
- [ ] Guide published

### Current Implementation Status

**Completed:**
- Description format standards defined
- Reading guide template created
- Runbook link standards established

**Current Documentation State:**
- Reading Guides:
  - bioetl-overview-v2.json: Has reading guide (partial)
  - bioetl-runtime.json: Has reading guide (partial)
  - Other dashboards: No reading guides - needs addition
- Panel Descriptions: Inconsistent format - needs standardization
- Dashboard Scope: Not clearly documented - needs addition
- Runbook Links: Inconsistent presence - needs standardization
- Comprehensive Dashboard Guide: Not created - needs creation

**Remaining:**
- Add reading guides to all dashboards (5 remaining)
- Standardize panel descriptions across all dashboards
- Add runbook links to appropriate panels
- Document dashboard scope for all dashboards
- Create comprehensive dashboard guide document
- Review and publish documentation

## 🎯 Notes

This issue improves dashboard usability by providing clear documentation and guidance. The dashboard guide should become the primary reference for operators using the observability stack.
