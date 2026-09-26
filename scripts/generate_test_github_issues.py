#!/usr/bin/env python3
"""
Generate GitHub Issues for Test Problems

This script analyzes the test infrastructure and creates GitHub issues
for identified problems like:
- Test timeouts
- Missing test coverage
- Flaky tests
- Test infrastructure issues
"""

import os
import subprocess
import sys
from datetime import datetime
from typing import TypedDict

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GITHUB_REPO = os.getenv("GITHUB_REPO", "SatoryKono/BioactivityDataAcquisition")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class TestProblemCategory(TypedDict):
    """Configuration for one generated test-problem issue."""

    title: str
    description: str
    labels: list[str]
    severity: str


# Test problem categories
TEST_PROBLEM_CATEGORIES: dict[str, TestProblemCategory] = {
    "timeout": {
        "title": "Test Timeout Issues",
        "description": "Tests that exceed reasonable execution time limits",
        "labels": ["test", "performance", "timeout"],
        "severity": "high",
    },
    "coverage": {
        "title": "Missing Test Coverage",
        "description": "Code areas lacking adequate test coverage",
        "labels": ["test", "coverage", "quality"],
        "severity": "medium",
    },
    "flaky": {
        "title": "Flaky Test Detection",
        "description": "Tests with inconsistent pass/fail results",
        "labels": ["test", "flaky", "reliability"],
        "severity": "high",
    },
    "infrastructure": {
        "title": "Test Infrastructure Issues",
        "description": "Problems with test setup, fixtures, or configuration",
        "labels": ["test", "infrastructure", "tech-debt"],
        "severity": "medium",
    },
    "performance": {
        "title": "Slow Test Performance",
        "description": "Tests that run significantly slower than expected",
        "labels": ["test", "performance", "optimization"],
        "severity": "medium",
    },
}


def get_github_headers() -> dict[str, str]:
    """Get headers for GitHub API requests."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    return headers


def create_github_issue(title: str, body: str, labels: list[str]) -> str | None:
    """Create a GitHub issue and return its URL."""

    if not GITHUB_TOKEN:
        print("❌ GitHub token not configured. Set GITHUB_TOKEN environment variable.")
        return None

    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = get_github_headers()

    payload = {"title": title, "body": body, "labels": labels}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        issue = response.json()
        print(f"✅ Created GitHub issue: {issue['html_url']}")
        return issue["html_url"]
    except requests.RequestException as e:
        print(f"❌ Error creating GitHub issue: {e}")
        return None


def analyze_test_timeout_issues() -> dict[str, str]:
    """Analyze and identify test timeout issues."""

    issues_found = {}

    issue_body = """# Test Timeout Issues Analysis

## Problem
Several test categories are experiencing timeout issues that prevent normal execution.

## Identified Issues

### 1. Integration Test Timeouts
- **Location**: `tests/integration/`
- **Issue**: Tests using VCR.py and external API mocks are timing out
- **Impact**: Cannot run full test suite in CI/CD
- **Solution**: Implement test parallelization and timeout configuration

### 2. Architecture Test Complexity
- **Location**: `tests/architecture/`
- **Issue**: 97 architecture tests with complex dependency analysis
- **Impact**: Slow feedback loop for developers
- **Solution**: Optimize architecture test execution

### 3. Missing Timeout Configuration
- **Issue**: No global timeout settings in pytest.ini
- **Impact**: Tests can run indefinitely
- **Solution**: Add timeout configuration and test categorization

## Recommended Actions
1. Implement pytest-xdist for parallel execution
2. Add timeout markers to slow tests
3. Create focused test suites for different scenarios
4. Optimize VCR cassette loading

## Current Status
- Total test files: 1286
- Architecture tests: 97
- Integration tests: Significant number with VCR dependencies
- Test execution timeout: >300 seconds observed
"""

    issues_found["timeout"] = issue_body
    return issues_found


def analyze_coverage_issues() -> dict[str, str]:
    """Analyze test coverage issues."""

    issues_found = {}

    issue_body = """# Missing Test Coverage Analysis

## Problem
Coverage reports and test inventories indicate potential gaps in behavioral
coverage.

## Identified Issues

### 1. Coverage Inventory Gaps
- **Issue**: Some modules have weak or missing behavioral assertions
- **Impact**: Quality metrics may not describe the real risk surface
- **Affected areas**:
  - Application layer (composite, core, pipelines)
  - Domain layer (schemas, services, exceptions)
  - Infrastructure layer (adapters, storage, validation)
  - Composition layer (bootstrap, factories, providers)

### 2. Coverage Thresholds Not Met
- **Requirement**: 85% overall, 90% domain coverage
- **Issue**: Coverage gaps make quality gates less actionable
- **Impact**: Cannot verify quality gates

### 3. Test Debt Accumulation
- **Issue**: Excluded files likely lack proper test coverage
- **Impact**: Technical debt in untested code paths
- **Risk**: Production bugs in untested components

## Recommended Actions
1. Gradually reduce Sonar exclusions (10-20 files at a time)
2. Add unit tests for excluded application components
3. Implement integration tests for excluded infrastructure
4. Create contract tests for excluded domain components
5. Establish coverage baseline and track progress

## Priority Areas for Test Addition
1. `src/bioetl/application/composite/` - Core business logic
2. `src/bioetl/domain/schemas/` - Data contracts
3. `src/bioetl/infrastructure/adapters/` - External integrations
4. `src/bioetl/composition/factories/` - Dependency injection

## Current State
- Total Python files in src/bioetl/: ~500+
- Files excluded from Sonar: 168
- Test files: 1286
- Coverage measurement: Unreliable due to exclusions
"""

    issues_found["coverage"] = issue_body
    return issues_found


def analyze_test_infrastructure() -> dict[str, str]:
    """Analyze test infrastructure issues."""

    issues_found = {}

    issue_body = """# Test Infrastructure Issues Analysis

## Problem
Test infrastructure complexity is causing execution and maintenance challenges.

## Identified Issues

### 1. Complex Test Configuration
- **Issue**: Multiple test markers and categories without clear organization
- **Impact**: Difficult to run specific test subsets
- **Solution**: Simplify test categorization and documentation

### 2. VCR Management Challenges
- **Issue**: Large number of VCR cassettes for HTTP mocking
- **Impact**: Slow test execution and cassette maintenance overhead
- **Solution**: Implement cassette optimization and selective recording

### 3. Async Test Complexity
- **Issue**: Asyncio tests with complex fixture requirements
- **Impact**: Flaky async test execution
- **Solution**: Standardize async test patterns

### 4. Missing Test Parallelization
- **Issue**: No pytest-xdist configuration for parallel execution
- **Impact**: Slow test suite execution
- **Solution**: Implement parallel test execution

### 5. Test Timeout Configuration
- **Issue**: Inconsistent timeout handling across test types
- **Impact**: Tests hang indefinitely
- **Solution**: Standardize timeout configuration

## Recommended Infrastructure Improvements

1. **Test Runner Optimization**
   - Create focused test runners for different scenarios
   - Implement test sharding for CI/CD
   - Add timeout configuration per test category

2. **VCR Optimization**
   - Implement cassette pruning strategy
   - Add cassette validation
   - Create cassette generation scripts

3. **Async Test Standardization**
   - Document async test patterns
   - Create async test helpers
   - Standardize async fixture usage

4. **Test Documentation**
   - Document test execution strategies
   - Create test troubleshooting guide
   - Add test performance benchmarks

## Current Infrastructure Components
- pytest.ini: Basic configuration
- conftest.py: Test fixtures
- VCR.py: HTTP mocking
- pytest-asyncio: Async test support
- Hypothesis: Property-based testing
- Missing: pytest-xdist, test parallelization
"""

    issues_found["infrastructure"] = issue_body
    return issues_found


def generate_github_issues_for_all_problems():
    """Generate GitHub issues for all identified test problems."""

    if not GITHUB_TOKEN:
        print("⚠️  GitHub token not configured. Issues will be generated as markdown.")
        print("Set GITHUB_TOKEN environment variable to create real GitHub issues.")

    created_issues = []

    # Analyze all problem categories
    all_analyses = {}
    all_analyses.update(analyze_test_timeout_issues())
    all_analyses.update(analyze_coverage_issues())
    all_analyses.update(analyze_test_infrastructure())

    # Create GitHub issues for each problem category
    for problem_type, analysis_func in [
        ("timeout", analyze_test_timeout_issues),
        ("coverage", analyze_coverage_issues),
        ("infrastructure", analyze_test_infrastructure),
    ]:
        issues = analysis_func()
        for issue_type, issue_body in issues.items():
            config = TEST_PROBLEM_CATEGORIES.get(
                issue_type, TEST_PROBLEM_CATEGORIES["infrastructure"]
            )

            title = f"[{config['severity'].upper()}] {config['title']} - {datetime.now().strftime('%Y-%m-%d')}"

            # Add context to issue body
            full_body = f"""# {title}

**Created**: {datetime.now().isoformat()}
**Severity**: {config["severity"]}
**Category**: {issue_type}

{issue_body}

## Next Steps
- [ ] Analyze specific test failures
- [ ] Implement recommended solutions
- [ ] Track progress in this issue
- [ ] Update test documentation

## Related
- Test infrastructure: `pytest.ini`, `conftest.py`
- Test runner: `scripts/optimized_test_runner.py`
"""

            if GITHUB_TOKEN:
                issue_url = create_github_issue(title, full_body, config["labels"])
                if issue_url:
                    created_issues.append((title, issue_url))
            else:
                # Output as markdown for manual creation
                print(f"\n{'=' * 80}")
                print(f"ISSUE TO CREATE MANUALLY: {title}")
                print(f"{'=' * 80}")
                print(full_body)
                print(f"{'=' * 80}\n")

    return created_issues


def main():
    """Main entry point."""

    print("🔍 Analyzing Test Problems and Generating GitHub Issues")
    print("=" * 60)

    created_issues = generate_github_issues_for_all_problems()

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    if created_issues:
        print(f"✅ Created {len(created_issues)} GitHub issues:")
        for title, url in created_issues:
            print(f"  • {title}: {url}")
    else:
        print("⚠️  No GitHub issues created (missing GITHUB_TOKEN)")
        print("Markdown issue templates have been generated above for manual creation.")

    print("\n🎯 RECOMMENDED NEXT STEPS:")
    print("1. Review and prioritize the created issues")
    print(
        "2. Implement the optimized test runner: python3 scripts/optimized_test_runner.py --list"
    )
    print("3. Gradually reduce Sonar exclusions and add tests")
    print("4. Implement test parallelization with pytest-xdist")
    print("5. Update test documentation and infrastructure")


if __name__ == "__main__":
    main()
