______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Class Diagram: 13 Domain Services

- Исходная диаграмма: `class-diagrams/13-domain-services.mmd`

## Описание

Диаграмма Domain Services показывает архитектурный срез семейства `bioetl.domain.services` и фиксирует роли pure domain services без I/O. Её следует читать как representative class view: схема помогает увидеть основные service families и точки расширения, но не является исчерпывающим каталогом всей текущей кодовой поверхности. Ключевые элементы для быстрого чтения: `EntityIdentityGenerator`, `BioactivityNormalizer`, `DefaultDataNormalizer`, `AuthorNormalizer`, `ActivityAggregator`, `UnitConverter`. Этот срез полезен при ревью инвариантов domain layer и проверке того, что новые сервисы не протаскивают инфраструктурные зависимости в `domain`.

## Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата метаданных: `2026-03-20`
