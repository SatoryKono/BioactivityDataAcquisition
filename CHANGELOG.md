# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Removed
- Удалена заглушка `assay_enrichment` из `ChemblSourceConfig`.
- Помечены deprecated несуществующие клиенты (PubChem, PubMed, Crossref, UniProt, SemanticScholar) в документации.

### Breaking Changes
- Поле `assay_enrichment` удалено из конфигурации. Если использовалось в YAML-конфигах — удалить.

