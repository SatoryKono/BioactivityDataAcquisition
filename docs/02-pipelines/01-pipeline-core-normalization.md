# 01 Pipeline Core Normalization

## Overview

Normalization is driven by `NormalizationServiceABC` (`bioetl.domain.transform.contracts`) backed by provider-specific services. The base factory `bioetl.infrastructure.transform.factories.default_normalization_service` wires the contract using the shared `NormalizationServiceImpl`, while ChEMBL-specific runs can switch to `ChemblNormalizationServiceImpl` when registered via `abc_impls.yaml`.

## Components

- **Contracts**: `NormalizationServiceABC`, `BaseNormalizationServiceABC`, `NormalizationConfigProviderProtocol` (field config access) — declared in `bioetl.domain.transform.contracts`.
- **Factories**: `default_normalization_service(config)` (`bioetl.infrastructure.transform.factories`) returning the default implementation.
- **Shared helpers**: `BaseNormalizationServiceImpl` (`bioetl.infrastructure.transform.impl.base_normalizer`) implementing `BaseNormalizationServiceABC` with deterministic normalization for scalars and containers, numeric coercion, and empty-value handling.
- **Implementations**:
  - `NormalizationServiceImpl` (`bioetl.infrastructure.transform.impl.normalization_service_impl`) — generic, config-driven normalization over DataFrames and series on top of the base helper.
  - `ChemblNormalizationServiceImpl` (`bioetl.infrastructure.transform.impl.chembl_normalization_service_impl`) — specialization that injects ChEMBL-specific normalizers and serialization rules for arrays/records while leveraging the base helper.
- **Normalizers**: reusable functions in `bioetl.domain.transform.normalizers` for arrays (`normalize_array`), records (`normalize_record`), and identifier-aware scalar normalization.

## Registry mapping

`src/bioetl/infrastructure/clients/base/abc_impls.yaml` now lists both `NormalizationServiceImpl` (Default) and `ChemblNormalizationServiceImpl` (Chembl) under the `NormalizationServiceABC` role to allow provider-specific selection in containers and orchestrator.
