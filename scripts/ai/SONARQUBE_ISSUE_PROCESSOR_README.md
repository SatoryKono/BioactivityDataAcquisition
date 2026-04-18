# SonarQube Issue Processor

## Overview

This solution automates the process of extracting SonarQube issues, grouping them by architectural layers, and creating GitHub issues for each layer. It helps teams efficiently track and resolve code quality issues.

## Files Created

### 1. `sonar_issue_processor.py`
**Main script** that performs the complete workflow:
- Fetches SonarQube issues via API
- Groups issues by project layers
- Creates GitHub issues automatically
- Provides detailed reporting

### 2. `sonar_issue_processor_demo.py`
**Demo version** that simulates the workflow without requiring real API credentials. Perfect for testing and understanding how the system works.

### 3. `improved_sonar_prompt.md`
**Enhanced prompt** documenting the complete workflow and requirements.

## How It Works

### Step-by-Step Process

1. **Fetch SonarQube Issues**
   - Connects to SonarQube/SonarCloud API
   - Retrieves all unresolved issues
   - Includes full issue details (severity, type, location, message)

2. **Group by Architectural Layers**
   - **Frontend**: `src/frontend`, `src/ui`, `src/components`
   - **Backend**: `src/backend`, `src/api`, `src/services`
   - **Database**: `src/database`, `src/models`, `src/repositories`
   - **Tests**: `src/tests`, `test`, `tests`
   - **Configuration**: `config`, `src/config`
   - **Utilities**: `src/utils`, `src/helpers`, `src/common`
   - **Unclassified**: Files not matching any pattern

3. **Create GitHub Issues**
   - One issue per layer with problems
   - Detailed issue information in markdown format
   - Appropriate labels (`sonarqube`, `quality`, `{layer}`)
   - Clear action items for resolution

4. **Generate Summary Report**
   - Total issues processed
   - Issues per layer breakdown
   - GitHub issue URLs created
   - Error reporting

## Demo Execution

The demo shows exactly how the system would work with real data:

```bash
python3 sonar_issue_processor_demo.py
```

**Demo Output Example:**
```
🚀 Starting SonarQube Issue Processor Demo
==================================================
🔍 Simulating SonarQube API call for project: bioactivitydataacquisition2
✅ Found 5 simulated SonarQube issues

📊 Issue Distribution by Layer:
----------------------------------------
  frontend    :  1 issues
  backend     :  2 issues
  database    :  1 issues
  utils       :  1 issues

🎯 Creating GitHub Issues:
----------------------------------------
📝 Simulating GitHub issue creation for frontend layer...
    Title: SonarQube Issues: frontend layer (1 issues)
    Issues: [MINOR] Unused variable 'temp' (src/frontend/components/UserProfile.jsx:15)
```

## Real Execution

To run with real SonarQube and GitHub data:

```bash
# Set required environment variables
export SONARQUBE_ORG="your-sonarcloud-org"
export SONARQUBE_TOKEN="your-sonarcloud-token"
export GITHUB_TOKEN="your-github-token"

# Run the processor
python3 sonar_issue_processor.py
```

## Customization

### Layer Mapping
Modify the `LAYER_MAPPING` dictionary in `sonar_issue_processor.py` to match your project structure:

```python
LAYER_MAPPING = {
    "frontend": ["src/frontend", "src/ui", "src/components"],
    "backend": ["src/backend", "src/api", "src/services"],
    # Add your custom layers here
}
```

### Issue Filtering
Adjust the API parameters to filter by specific severities or types:

```python
params = {
    "componentKeys": project_key,
    "severities": "CRITICAL,MAJOR",  # Only critical and major issues
    "types": "BUG,VULNERABILITY",     # Only bugs and vulnerabilities
    "resolved": "false"
}
```

### GitHub Configuration
Change the repository and issue template:

```python
GITHUB_REPO = os.getenv("GITHUB_REPO", "your-repo-name")
```

## Requirements

- Python 3.7+
- `requests` library (usually pre-installed)
- SonarQube/SonarCloud account with API access
- GitHub account with repository access

## Benefits

1. **Automated Workflow**: No manual issue tracking
2. **Architectural Focus**: Issues grouped by logical layers
3. **Detailed Documentation**: Full issue context in GitHub tickets
4. **Traceability**: Direct link between SonarQube and GitHub
5. **Prioritization**: Clear severity indicators
6. **Team Efficiency**: Developers can focus on specific layers

## Example GitHub Issue Format

```markdown
# SonarQube Issues in Backend Layer

**Total Issues:** 2

## Issues Detail

### Issue 1
- **Severity:** MAJOR
- **Type:** BUG
- **Location:** `src/backend/services/UserService.java:42`
- **Message:** Potential null pointer dereference

### Issue 2
- **Severity:** CRITICAL
- **Type:** VULNERABILITY
- **Location:** `src/backend/api/UserController.java:87`
- **Message:** SQL injection vulnerability

## Action Required
- Review and fix the identified issues
- Update code to comply with quality standards
- Run SonarQube analysis after fixes to verify resolution
```

## Troubleshooting

### Missing Environment Variables
```
❌ SonarQube configuration missing. Please set SONARQUBE_ORG and SONARQUBE_TOKEN.
```
**Solution**: Set the required environment variables before running.

### API Connection Issues
```
Error fetching SonarQube issues: 401 Unauthorized
```
**Solution**: Verify your SonarQube token has proper permissions.

### GitHub API Errors
```
Error creating GitHub issue: 404 Not Found
```
**Solution**: Check your GitHub token and repository name.

## Future Enhancements

- Add JIRA integration option
- Support for multiple projects
- Issue assignment based on layer ownership
- Automatic issue updates when SonarQube issues are resolved
- Slack/Teams notifications for new issues

## License

This solution is provided as-is and can be freely used and modified for your projects.