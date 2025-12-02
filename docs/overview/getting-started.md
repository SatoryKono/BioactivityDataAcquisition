# Getting Started

Quick start guide for BioETL.

## Prerequisites

- Python 3.9+
- Git

## Installation

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition
cd BioactivityDataAcquisition
pip install -e .
```

## Running Your First Pipeline

### Validate Configuration

```bash
bioetl validate-config configs/pipelines/chembl/activity.yaml
```

### Run a Pipeline

```bash
# Development profile (quick test)
bioetl run activity_chembl --profile development

# Production profile (full run)
bioetl run activity_chembl --profile production
```

## Next Steps

- Read the [Architecture Overview](architecture-overview.md) to understand system design
- Check [Running Pipelines](../guides/running-pipelines.md) for detailed usage
- Explore [Configuration Guide](../guides/configuration.md) for customizing pipelines
- Review [Project Rules](../project/rules-summary.md) for development standards

