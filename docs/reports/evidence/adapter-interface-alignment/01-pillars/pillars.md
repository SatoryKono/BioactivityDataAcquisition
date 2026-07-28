# Pillars

## adapter-interface-alignment

- Priority: High
- Scope: Provider registry contracts, composition-layer adapter/data-source creators, specialized non-bibliographic creator paths, and composite runtime bootstrap/service-bundle seams.
- Scope restrictions:
  - In scope: `src/bioetl/composition/providers/**`, `src/bioetl/composition/factories/datasource/**`, `src/bioetl/composition/bootstrap/runtime/**`, `src/bioetl/infrastructure/adapters/{openalex,pubmed,pubchem,semanticscholar,uniprot}/**`, and supporting unit tests.
  - Out of scope: pipeline business logic, Bronze/Silver/Gold transforms, and composite phase execution internals after runner bootstrap.

### Research Questions

1. Which seams already expose an explicit interface contract for adapter and data-source creation?
1. Where are helper dependencies such as `fallback_fetch_service`, `error_handler`, and `adapter_metrics` synthesized?
1. Which seams rely on implicit runtime kwargs instead of an explicit protocol?
1. How do concrete HTTP adapters express mandatory collaborator requirements?
1. Which tests encode the intended public surface for provider-bound creators?
1. How do non-bibliographic creators assemble specialized collaborators when they do not use the generic HTTP helper path?
1. How do composite runtime creators keep public interfaces stable while hiding helper-only bootstrap details?
