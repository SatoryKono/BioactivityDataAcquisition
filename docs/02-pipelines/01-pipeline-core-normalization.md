# 01 Pipeline Core Normalization

## Overview

Normalization is driven by `NormalizationServiceABC` (`bioetl.domain.transform.contracts`) backed by provider-specific services. The base factory `bioetl.infrastructure.transform.factories.default_normalization_service` wires the contract using the shared `NormalizationServiceImpl`, while ChEMBL-specific runs can switch to `ChemblNormalizationService` when registered via `abc_impls.yaml`.

## Components

- **Contracts**: `NormalizationServiceABC`, `NormalizationConfigProvider` (field config access) — declared in `bioetl.domain.transform.contracts`.
- **Factories**: `default_normalization_service(config)` (`bioetl.infrastructure.transform.factories`) returning the default implementation.
- **Shared helpers**: `BaseNormalizationService` (`bioetl.infrastructure.transform.impl.base_normalizer`) providing deterministic normalization for scalars and containers, numeric coercion, and empty-value handling.
- **Implementations**:
  - `NormalizationServiceImpl` (`bioetl.infrastructure.transform.impl.normalization_service_impl`) — generic, config-driven normalization over DataFrames and series.
  - `ChemblNormalizationService` (`bioetl.infrastructure.transform.impl.chembl_normalization_service`) — specialization that injects ChEMBL-specific normalizers and serialization rules for arrays/records.
- **Normalizers**: reusable functions in `bioetl.domain.transform.normalizers` for arrays (`normalize_array`), records (`normalize_record`), and identifier-aware scalar normalization.

## Registry mapping

`src/bioetl/infrastructure/clients/base/abc_impls.yaml` now lists both `NormalizationServiceImpl` (Default) and `ChemblNormalizationService` (Chembl) under the `NormalizationServiceABC` role to allow provider-specific selection in containers and orchestrator.
