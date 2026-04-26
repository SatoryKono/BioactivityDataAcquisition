______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Reproducible Run Contract Overview

- Исходная диаграмма: `views/23-reproducible-run-contract-overview.mermaid`

## Описание

Эта views-диаграмма Reproducible Run Contract Overview представляет срез типа overview для родительской схемы 23-reproducible-run-contract.mmd и использует нотацию flowchart. Она нужна как краткая карта reproducibility anchors, по которым можно сравнивать и воспроизводить запуск без просмотра полной control-plane схемы. В метке view зафиксировано назначение: Overview. Показательные узлы в диаграмме: Config inputs + source refs, Resolved + effective config, Identity hashes, Run manifest, Replay / diff consumers. Такой срез полезен для ревью reproducibility contract и проверки, что execution fingerprint и related hashes остаются центральными якорями архитектуры.

## Метаданные

- Тип: `flowchart`
- View: `Overview`
- Parent: `23-reproducible-run-contract.mmd`
