# Link Checker Plugin - Integration Guide

## 🎯 Overview

This guide provides step-by-step instructions for integrating the BioETL Link Checker Plugin into your MkDocs documentation system. The plugin validates all links during the build process and exposes results as published link health metrics.

## 📋 Prerequisites

### Required Dependencies

```bash
pip install beautifulsoup4 requests
```

### Python Version

- Python 3.11 or higher
- MkDocs 1.4.0 or higher

### System Requirements

- Minimum 2GB RAM for large documentation sites
- Internet connection for external link validation
- Git for version control

## 🛠️ Installation

### Option 1: Install from Source (Recommended)

```bash
# Clone the repository (if not already cloned)
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition

# Install the plugin in development mode
pip install -e docs/plugins/link_checker
```

### Option 2: Install as Package

```bash
# Install directly from the plugin directory
pip install docs/plugins/link_checker/
```

### Option 3: Manual Installation

```bash
# Copy the plugin to your Python path
cp -r docs/plugins/link_checker /path/to/your/python/site-packages/
```

## 🔧 Configuration

### Basic Configuration

Add the plugin to your `mkdocs.yml`:

```yaml
# mkdocs.yml
plugins:
  - link_checker:
      enabled: true              # Enable the plugin
      timeout: 15               # HTTP timeout in seconds
      max_redirects: 5          # Maximum redirects to follow
      ignore_patterns:         # URL patterns to ignore
        - "localhost"
        - "127.0.0.1"
        - "staging\.example\.com"
      report_dir: "reports/links"  # Directory for reports
      fail_on_error: false      # Set to true to fail build on broken links
```

### Advanced Configuration

```yaml
# mkdocs.yml
plugins:
  - link_checker:
      enabled: true
      timeout: 30               # Longer timeout for slow services
      max_redirects: 3          # Fewer redirects for security
      ignore_patterns:
        - "localhost"
        - "127.0.0.1"
        - "staging\.example\.com"
        - "\.local$"
        - "192\.168\."
        - "10\."
        - "api\.internal\.com"
      report_dir: "quality/links"
      fail_on_error: true       # Fail CI/CD on broken links
```

### Configuration Options

| Option            | Type | Default                      | Description                           |
| ----------------- | ---- | ---------------------------- | ------------------------------------- |
| `enabled`         | bool | `true`                       | Enable/disable the plugin             |
| `timeout`         | int  | `10`                         | HTTP request timeout in seconds       |
| `max_redirects`   | int  | `5`                          | Maximum number of redirects to follow |
| `ignore_patterns` | list | `['localhost', '127.0.0.1']` | URL patterns to ignore                |
| `report_dir`      | str  | `'reports/links'`            | Directory to save reports             |
| `fail_on_error`   | bool | `false`                      | Fail build if broken links found      |

## 🚀 Usage

### Basic Usage

```bash
# Build documentation with link checking
mkdocs build

# View the link health report
cat site/reports/links/link-health.json

# Open the HTML report
open site/reports/links/link-health.html
```

### Development Mode

```bash
# Build with strict mode (fails on broken links if configured)
mkdocs build --strict

# Serve documentation locally
mkdocs serve
```

### CI/CD Usage

```bash
# Build and fail on any broken links
mkdocs build --strict
```

## 🔍 Reports

The plugin generates three types of reports:

### 1. JSON Report (`link-health.json`)

Machine-readable report with complete link inventory:

```json
{
  "version": "1.0",
  "generated_at": "2026-04-24T10:00:00Z",
  "duration_seconds": 12.5,
  "summary": {
    "total_links": 42,
    "valid_links": 38,
    "broken_links": 2,
    "redirect_links": 2,
    "health_score": 90.5,
    "internal_links": 25,
    "external_links": 17
  },
  "details": [
    {
      "source_file": "index.html",
      "source_path": "site/index.html",
      "link_url": "https://example.com",
      "link_text": "Example",
      "status": "valid",
      "http_code": 200,
      "redirect_chain": [],
      "is_internal": false,
      "error": null
    }
  ]
}
```

### 2. HTML Report (`link-health.html`)

Interactive web report with:

- Summary statistics
- Color-coded status indicators
- Sortable/filterable table
- Clickable links for verification

### 3. SVG Badge (`link-badge.svg`)

Visual status indicator showing health score:

- **Green** (≥95%): Passing
- **Yellow** (80-95%): Warning
- **Red** (\<80%): Failing

## 🤖 CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/docs-ci.yml
name: Documentation CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install mkdocs mkdocs-material
          pip install beautifulsoup4 requests

      - name: Install link checker plugin
        run: pip install -e docs/plugins/link_checker

      - name: Build documentation with link checking
        run: mkdocs build --strict

      - name: Upload link health report
        uses: actions/upload-artifact@v3
        with:
          name: link-health-report
          path: site/reports/links/

      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main'
        run: mkdocs gh-deploy
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
stages:
  - test
  - deploy

build_docs:
  stage: test
  image: python:3.11
  script:
    - pip install mkdocs mkdocs-material beautifulsoup4 requests
    - pip install -e docs/plugins/link_checker
    - mkdocs build --strict
  artifacts:
    paths:
      - site/reports/links/
    when: always

deploy_docs:
  stage: deploy
  image: python:3.11
  script:
    - pip install mkdocs mkdocs-material beautifulsoup4 requests
    - pip install -e docs/plugins/link_checker
    - mkdocs gh-deploy --force
  only:
    - main
```

## 🎯 Best Practices

### Configuration Tips

1. **Start with fail_on_error: false** during development
1. **Use ignore_patterns** for local/development URLs
1. **Set reasonable timeouts** (10-15 seconds)
1. **Monitor report_dir** for performance metrics
1. **Review reports regularly** to catch link rot early

### Performance Optimization

1. **Use ignore_patterns** to skip unnecessary checks
1. **Increase timeout** for slow external services
1. **Run in CI/CD** to avoid local delays
1. **Use fail_on_error: false** during active development
1. **Monitor health score** trends over time

### Troubleshooting

**Issue: Plugin not loading**

- Solution: Ensure plugin path is correct and dependencies are installed
- Check: `python3 -c "from docs.plugins.link_checker.plugin import LinkCheckerPlugin"`

**Issue: Slow link checking**

- Solution: Increase timeout or reduce max_workers
- Check: Monitor `duration_seconds` in JSON report

**Issue: False positives**

- Solution: Add patterns to `ignore_patterns`
- Check: Review `details` section in JSON report

**Issue: Build fails due to broken links**

- Solution: Set `fail_on_error: false` or fix broken links
- Check: Look for `"status": "broken"` in JSON report

## 📚 Examples

### Minimal Configuration

```yaml
# mkdocs.yml
plugins:
  - link_checker:
      enabled: true
```

### Production Configuration

```yaml
# mkdocs.yml
plugins:
  - link_checker:
      enabled: true
      timeout: 15
      max_redirects: 5
      ignore_patterns:
        - "localhost"
        - "127.0.0.1"
        - "staging\.example\.com"
      report_dir: "reports/links"
      fail_on_error: true
```

### Development Configuration

```yaml
# mkdocs.yml
plugins:
  - link_checker:
      enabled: true
      timeout: 10
      max_redirects: 3
      ignore_patterns:
        - "localhost"
        - "127.0.0.1"
        - "\.local$"
        - "192\.168\."
      fail_on_error: false  # Don't fail during development
```

## 📖 Advanced Usage

### Custom Report Processing

```python
import json

# Load the JSON report
with open("site/reports/links/link-health.json") as f:
    report = json.load(f)

# Analyze results
health_score = report["summary"]["health_score"]
broken_links = report["summary"]["broken_links"]

if health_score < 90:
    print(f"⚠️  Link health low: {health_score}%")
    for link in report["details"]:
        if link["status"] == "broken":
            print(f"  Broken: {link['link_url']} in {link['source_file']}")
else:
    print(f"✅ Link health good: {health_score}%")
```

### Programmatic Access

```python
from docs.plugins.link_checker.plugin import LinkCheckerPlugin

# Create plugin instance
plugin = LinkCheckerPlugin()
plugin.config = {"enabled": True, "timeout": 10, "fail_on_error": False}

# Use plugin methods programmatically
# (Note: This requires MkDocs context for full functionality)
```

## 🎓 Support

### Documentation

- **Plugin README**: Complete documentation in `README.md`
- **Issue #3094**: Original issue specification
- **BioETL Docs**: Main documentation site

### Getting Help

1. **Check the FAQ** in `README.md`
1. **Review examples** in this guide
1. **Consult the test suite** for usage patterns
1. **Open an issue** for bugs or feature requests

### Contributing

Contributions are welcome! See `CONTRIBUTING.md` for guidelines.

## 🏆 Success Criteria

### Functional Requirements

- ✅ All internal links validated during build
- ✅ External links checked with configurable timeout
- ✅ Redirect chains detected and reported
- ✅ Link health report generated in JSON/HTML formats
- ✅ Status badges embedded in published documentation
- ✅ CI/CD pipeline integration with fail-on-error option

### Quality Metrics

- ✅ 100% of internal links validated
- ✅ 95%+ of external links checked
- ✅ Link health score > 95% for production
- ✅ Zero broken links in production documentation
- ✅ Automated verification in CI/CD pipeline

## 🎯 Conclusion

The BioETL Link Checker Plugin provides comprehensive link validation for your documentation. By following this integration guide, you can:

1. **Automate link checking** during documentation builds
1. **Improve documentation quality** with health metrics
1. **Catch broken links early** before users encounter them
1. **Integrate with CI/CD** for automated quality gates
1. **Monitor link health** over time with detailed reports

For more information, refer to the complete documentation in `README.md` or consult the test suite for advanced usage examples.
