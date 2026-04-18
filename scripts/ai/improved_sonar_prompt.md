# Improved SonarQube Issue Processing Prompt

## Enhanced Prompt for Sonar Issue Extraction and GitHub Issue Creation

**Goal**: Extract all SonarQube issues from the project, group them by architectural layers, and automatically create GitHub issues for each layer with detailed issue information.

## Step-by-Step Process

### 1. Fetch SonarQube Issues
- Use SonarQube API to retrieve all unresolved issues
- Filter by severity (CRITICAL, MAJOR, MINOR, INFO)
- Include issue details: type, location, message, severity

### 2. Group Issues by Project Layers
- **Layer Classification**:
  - **Frontend**: `src/frontend`, `src/ui`, `src/components`
  - **Backend**: `src/backend`, `src/api`, `src/services`  
  - **Database**: `src/database`, `src/models`, `src/repositories`
  - **Tests**: `src/tests`, `test`, `tests`
  - **Configuration**: `config`, `src/config`
  - **Utilities**: `src/utils`, `src/helpers`, `src/common`
  - **Unclassified**: Any files not matching above patterns

### 3. Create GitHub Issues
For each layer with issues, create a GitHub issue with:
- **Title**: `SonarQube Issues: {layer} layer ({count} issues)`
- **Labels**: `sonarqube`, `quality`, `{layer}`
- **Body Structure**:
  ```markdown
  # SonarQube Issues in {layer} Layer
  
  **Total Issues:** {count}
  
  ## Issues Detail
  
  ### Issue 1
  - **Severity:** {severity}
  - **Type:** {type}
  - **Location:** `{file_path}:{line}`
  - **Message:** {message}
  
  ## Action Required
  - Review and fix the identified issues
  - Update code to comply with quality standards
  - Run SonarQube analysis after fixes to verify resolution
  ```

### 4. Output Summary
Provide a summary report showing:
- Total issues found
- Issues per layer breakdown
- GitHub issue URLs created
- Any errors encountered

## Implementation

The script `sonar_issue_processor.py` automates this entire workflow:

### Using .env file (recommended):

1. Create `.env` file:
```bash
SONARQUBE_TOKEN="your-sonarcloud-token"
GITHUB_TOKEN="your-github-token"
```

2. Run the processor:
```bash
python3 sonar_issue_processor.py
```

### Using environment variables:

```bash
# Set required environment variables
export SONARQUBE_TOKEN="your-sonarcloud-token"
export GITHUB_TOKEN="your-github-token"

# Run the processor
python3 sonar_issue_processor.py
```

## Customization

- **Layer Mapping**: Modify `LAYER_MAPPING` in the script to match your project structure
- **Issue Filtering**: Adjust API parameters to filter by specific severities or types
- **GitHub Repository**: Change `GITHUB_REPO` environment variable for different repositories

## Benefits

1. **Automated Issue Tracking**: No manual issue creation
2. **Layer-Specific Focus**: Issues grouped by architectural concerns
3. **Detailed Documentation**: Each GitHub issue contains full issue details
4. **Traceability**: Direct links between SonarQube issues and GitHub tickets
5. **Prioritization**: Clear severity indicators for each issue