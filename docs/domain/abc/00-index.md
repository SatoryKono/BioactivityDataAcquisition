# Domain Contracts (ABC)

Catalog актуальных ABC и их реализаций.

- Реестры машинного уровня: `src/bioetl/infrastructure/clients/base/abc_registry.yaml` и `abc_impls.yaml` (соответствие ABC ↔ default factory ↔ impl).
- Клиентский контракт: `ChemblDataClientABC` (`src/bioetl/domain/clients/chembl/contracts.py`).
- Пайплайновые хуки и политики: `PipelineHookABC`, `ErrorPolicyABC` (`src/bioetl/application/pipelines/hooks.py`).
- Валидация: `ValidatorABC`, `SchemaProviderABC` (`src/bioetl/domain/validation/contracts.py`).
- Нормализация/трансформации: `TransformerABC` (`src/bioetl/domain/transform/transformers.py`).
- Экстракция: `ExtractorABC` (`src/bioetl/application/pipelines/contracts.py`).

При добавлении нового ABC:
1. Создайте контракт в соответствующем модуле.
2. Добавьте default factory в `abc_impls.yaml` (может быть stub).
3. Опишите Impl в `impl/` и зарегистрируйте в `abc_registry.yaml`.
4. Обновите документацию здесь ссылкой на контракт и путь к Default/Impl.

