# BioETL Link Checker Plugin

## Overview

The BioETL Link Checker Plugin is an MkDocs plugin that validates all links in your documentation during the build process and exposes the results as published link health metrics.

**Issue #3094**: Expose Link-Check Results as Published

## Features

- ✅ **Automatic Link Validation**: Checks all internal and external links during documentation build
- ✅ **Comprehensive Reporting**: Generates JSON, HTML, and SVG badge reports
- ✅ **Parallel Processing**: Uses thread pool for fast link checking
- ✅ **Configurable**: Timeout, redirect limits, ignore patterns
- ✅ **CI/CD Integration**: Can fail build on broken links
- ✅ **Health Metrics**: Calculates link health score

## Installation

### As a Python Package

```bash
# Install from source
pip install -e docs/plugins/link_checker
```

### MkDocs Configuration

Add to your `mkdocs.yml`:

```yaml
plugins:
  - link_checker:
      enabled: true
      timeout: 10
      max_redirects: 5
      ignore_patterns:
        - "localhost"
        - "127.0.0.1"
      report_dir: "reports/links"
      fail_on_error: false
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable the plugin |
| `timeout` | int | `10` | HTTP request timeout in seconds |
| `max_redirects` | int | `5` | Maximum redirects to follow |
| `ignore_patterns` | list | `["localhost", "127.0.0.1"]` | Patterns to ignore |
| `report_dir` | str | `"reports/links"` | Directory for reports |
| `fail_on_error` | bool | `false` | Fail build on broken links |

## Usage

### Basic Usage

```bash
# Build documentation with link checking
mkdocs build

# View link health report
cat site/reports/links/link-health.json

# Open HTML report
open site/reports/links/link-health.html
```

### CI/CD Integration

```yaml
# .github/workflows/docs.yml
- name: Build and check links
  run: mkdocs build --strict
  
- name: Upload link report
  uses: actions/upload-artifact@v3
  with:
    name: link-health-report
    path: site/reports/links/
```

## Reports Generated

### 1. JSON Report (`link-health.json`)

Machine-readable report with detailed link information:

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

Human-readable HTML report with interactive table:

- Summary statistics with color-coded status
- Detailed table of all links
- Filterable and sortable
- Clickable links for easy verification

### 3. SVG Badge (`link-badge.svg`)

Visual status badge showing health score:

```html
<img src="reports/links/link-badge.svg" alt="Link Health">
```

Badge colors:
- **Green** (≥95%): Passing
- **Yellow** (80-95%): Warning  
- **Red** (<80%): Failing

## Examples

### Basic Configuration

```yaml
# mkdocs.yml
plugins:
  - link_checker:
      enabled: true
      fail_on_error: true
```

### Advanced Configuration

```yaml
# mkdocs.yml
plugins:
  - link_checker:
      enabled: true
      timeout: 15
      max_redirects: 3
      ignore_patterns:
        - "localhost"
        - "127.0.0.1"
        - "staging.example.com"
      report_dir: "quality/links"
      fail_on_error: false
```

### CI/CD with GitHub Actions

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
        run: pip install mkdocs mkdocs-material
      
      - name: Install link checker plugin
        run: pip install -e docs/plugins/link_checker
      
      - name: Build documentation
        run: mkdocs build --strict
      
      - name: Upload link report
        uses: actions/upload-artifact@v3
        with:
          name: link-health-report
          path: site/reports/links/
      
      - name: Deploy
        if: github.ref == 'refs/heads/main'
        run: mkdocs gh-deploy
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest requests beautifulsoup4

# Run tests
pytest docs/plugins/link_checker/tests/
```

### Plugin Structure

```
docs/plugins/link_checker/
├── plugin.py            # Main plugin code
├── README.md           # This file
├── requirements.txt    # Dependencies
└── tests/              # Test suite
    ├── test_plugin.py   # Plugin tests
    └── test_data/       # Test fixtures
```

### Dependencies

```
# requirements.txt
requests>=2.28.0
beautifulsoup4>=4.11.0
mkdocs>=1.4.0
```

## Troubleshooting

### Common Issues

**Issue**: Plugin not loading
- **Solution**: Ensure plugin is in `mkdocs.yml` and Python path is correct

**Issue**: Slow link checking
- **Solution**: Increase timeout or reduce max_workers

**Issue**: False positives on valid links
- **Solution**: Add patterns to `ignore_patterns` or adjust timeout

**Issue**: Build fails due to broken links
- **Solution**: Set `fail_on_error: false` or fix broken links

### Debugging

```bash
# Enable debug logging
mkdocs build --verbose

# Check plugin logs
grep "link_checker" build.log
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Commit changes**: `git commit -m 'Add some feature'`
4. **Push to branch**: `git push origin feature/your-feature`
5. **Open a pull request**

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Include docstrings
- Write unit tests

## License

This plugin is licensed under the MIT License. See the [LICENSE](../../../LICENSE) file for details.

## Support

For issues or questions:

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check the [BioETL Docs](../../../04-reference/index.md)
- **Community**: Join the discussion in our community forums

## Changelog

### v1.0.0 (2026-04-24)
- Initial release
- Basic link checking functionality
- JSON/HTML/SVG report generation
- MkDocs plugin integration

### Future Roadmap
- v1.1.0: Advanced link analysis (anchor validation, deep linking)
- v1.2.0: Historical trend tracking
- v1.3.0: Webhook notifications for broken links

## Related Issues

- **Issue #3094**: Expose Link-Check Results as Published
- **Parent Issue**: Documentation Audit 2026-04-23
- **Implementation Plan**: docs/reports/audit-issues/implementation-plans.md

## Success Metrics

- ✅ 100% of internal links validated
- ✅ 95%+ of external links checked
- ✅ Link health score > 95% for production
- ✅ Zero broken links in production documentation
- ✅ Automated verification in CI/CD pipeline

## Contact

For more information about this plugin or the BioETL project:

- **Documentation**: [BioETL Docs](../../../04-reference/index.md)
- **Source Code**: [GitHub Repository](https://github.com/SatoryKono/BioactivityDataAcquisition)
- **Issue Tracker**: [GitHub Issues](https://github.com/SatoryKono/BioactivityDataAcquisition/issues)

© 2026 BioETL Team. All rights reserved.