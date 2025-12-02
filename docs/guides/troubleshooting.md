# Troubleshooting

Common issues and solutions when working with BioETL.

## Configuration Issues

### Configuration Not Found

**Problem**: Pipeline fails with "Configuration file not found"

**Solution**: 
- Verify the path in `--config` flag
- Check that the file exists in `configs/pipelines/<provider>/<entity>.yaml`
- Ensure profile files exist if using `--profile`

### Invalid Configuration

**Problem**: Validation errors when loading configuration

**Solution**:
- Run `bioetl validate-config <path>` to check configuration
- Verify YAML syntax
- Check that all required fields are present
- Review configuration precedence rules in [Configuration Guide](configuration.md)

## Pipeline Execution Issues

### Pipeline Fails During Extraction

**Problem**: Errors when fetching data from external API

**Solution**:
- Check network connectivity
- Verify API credentials/secrets are set correctly
- Review rate limiting settings
- Check retry policy configuration
- Review logs for specific error messages

### Validation Errors

**Problem**: Data fails schema validation

**Solution**:
- Review validation error messages for specific column/row issues
- Check data transformation logic in normalizer
- Verify schema definition matches actual data structure
- Review [Schema Registry](../reference/core/schema-registry.md) documentation

### Determinism Failures

**Problem**: Golden run fails due to non-deterministic output

**Solution**:
- Ensure stable sorting is enabled in configuration
- Verify UTC timestamps are used
- Check that column order matches schema
- Review [Project Rules](../project/rules-summary.md) on determinism

## Development Issues

### Import Errors

**Problem**: Cannot import BioETL modules

**Solution**:
- Verify installation: `pip install -e .`
- Check Python path
- Ensure you're in the correct virtual environment

### Test Failures

**Problem**: Tests fail after code changes

**Solution**:
- Run tests with verbose output: `pytest -v`
- Check for network calls in unit tests (should be mocked)
- Verify test data is up to date
- Review [Testing Rules](../project/rules-summary.md)

## Getting Help

- Review relevant documentation in [Reference](../reference/)
- Check [Project Rules](../project/rules-summary.md) for standards
- Review [Architecture Overview](../overview/architecture-overview.md) for system design

