# Instructions for Creating GitHub Issues

✅ **STATUS: COMPLETED** - All issues successfully created on 2026-08-08

The following issue files have been prepared in `.github/issues/`:

1. **devin-optimization-overview.md** - Comprehensive optimization plan (parent issue)
2. **devin-optimization-quick-wins.md** - Phase 1: Quick Wins implementation
3. **devin-optimization-workflow.md** - Phase 2: Workflow Optimization
4. **devin-optimization-config.md** - Phase 3: Configuration Optimization

## Created Issues:

- **#8395** - Devin CLI Optimization: Comprehensive Efficiency Improvement Plan (parent issue)
- **#8396** - Devin CLI Optimization: Quick Wins for BioETL (Phase 1)
- **#8397** - Devin CLI Optimization: Workflow Templates and Error Recovery (Phase 2)
- **#8398** - Devin CLI Optimization: Permission Profiles and Smart MCP Management (Phase 3)

## Issue Dependencies:

- #8395 (parent) → blocks #8396, #8397, #8398
- #8396 (Phase 1) → blocks #8397
- #8397 (Phase 2) → blocks #8398
- #8398 (Phase 3) → final phase

## Comments Added:

- #8396: Linked to parent issue #8395, noted as Phase 1
- #8397: Linked to parent issue #8395, noted as Phase 2, depends on #8396
- #8398: Linked to parent issue #8395, noted as Phase 3, depends on #8397

## To create GitHub issues (ARCHIVED - already completed):

### Option 1: Using GitHub CLI (recommended)
```bash
# First authenticate with GitHub
gh auth login

# Create the overview issue first (parent issue)
gh issue create --title "Devin CLI Optimization: Comprehensive Efficiency Improvement Plan" --body-file .github/issues/devin-optimization-overview.md --label "enhancement" --label "CLI/UX"

# Create Phase 1 issue
gh issue create --title "Devin CLI Optimization: Quick Wins for BioETL" --body-file .github/issues/devin-optimization-quick-wins.md --label "enhancement" --label "CLI/UX"

# Create Phase 2 issue
gh issue create --title "Devin CLI Optimization: Workflow Templates and Error Recovery" --body-file .github/issues/devin-optimization-workflow.md --label "enhancement" --label "CLI/UX"

# Create Phase 3 issue
gh issue create --title "Devin CLI Optimization: Permission Profiles and Smart MCP Management" --body-file .github/issues/devin-optimization-config.md --label "enhancement" --label "CLI/UX" --label "infrastructure"
```

### Option 2: Manual creation via GitHub web interface
1. Go to https://github.com/SatoryKono/BioactivityDataAcquisition/issues/new/choose
2. Select "Feature Request" template
3. Copy content from each issue file
4. Fill in the form fields accordingly
5. Create issues in order: overview → quick-wins → workflow → config
6. Link issues using GitHub's issue references (e.g., #123)

### Option 3: Using GitHub API
```bash
# Requires GitHub personal access token
export GITHUB_TOKEN="your_token_here"

# Create issues using API
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues \
  -d '{"title":"Devin CLI Optimization: Comprehensive Efficiency Improvement Plan","body":"'"$(cat .github/issues/devin-optimization-overview.md)"'","labels":["enhancement","CLI/UX"]}'
```

## Issue Dependencies

- **devin-optimization-overview** (parent issue)
  - Blocks: devin-optimization-quick-wins
  - Blocks: devin-optimization-workflow  
  - Blocks: devin-optimization-config

- **devin-optimization-quick-wins** (Phase 1)
  - Depends on: devin-optimization-overview
  - Blocks: devin-optimization-workflow

- **devin-optimization-workflow** (Phase 2)
  - Depends on: devin-optimization-overview
  - Depends on: devin-optimization-quick-wins
  - Blocks: devin-optimization-config

- **devin-optimization-config** (Phase 3)
  - Depends on: devin-optimization-overview
  - Depends on: devin-optimization-workflow

## Recommended Labels

- `enhancement` - For all optimization issues
- `CLI/UX` - For CLI and usability improvements
- `infrastructure` - For configuration and MCP changes
- `good first issue` - For Phase 1 (Quick Wins)
- `medium effort` - For Phase 2 (Workflow Optimization)
- `high effort` - For Phase 3 (Configuration Optimization)

## Milestone Suggestions

Create a milestone "Devin CLI Optimization Q3 2026" and assign all issues to it for tracking.

## Next Steps After Issue Creation

1. **Assign issues** to appropriate team members
2. **Set up project board** if using GitHub Projects
3. **Create tracking** for implementation progress
4. **Set up weekly reviews** for each phase
5. **Document decisions** in issue comments
6. **Close issues** as each phase completes

## Notes

- All issues are ready to create with complete content
- Issues follow GitHub's feature request template format
- Implementation plans are detailed and actionable
- Risk assessments and success criteria are included
- Related files and dependencies are documented
